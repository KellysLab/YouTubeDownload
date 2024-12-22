from fastapi import FastAPI, Request, HTTPException, WebSocket
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import yt_dlp
import os
import asyncio
from datetime import timedelta
import humanize
import json
from fastapi.middleware.cors import CORSMiddleware
import logging
from tkinter import filedialog
import tkinter as tk
import subprocess
import platform

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# 添加 CORS 中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头部
)

# 配置静态文件和模板
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 存储下载的视频信息
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# 存储视频信息的列表
videos = []

# 存储WebSocket连接
active_connections = []

# 添加默认下载路径配置
DEFAULT_DOWNLOAD_PATHS = [
    DOWNLOAD_DIR
]

class ConnectionManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        manager.disconnect(websocket)

@app.get("/")
async def home(request: Request):
    logger.info("Accessing home page")
    try:
        response = templates.TemplateResponse("index.html", {"request": request, "videos": videos})
        logger.info("Template rendered successfully")
        return response
    except Exception as e:
        logger.error(f"Error rendering template: {str(e)}")
        raise

@app.get("/download-paths")
async def get_download_paths():
    """获取可用的下载路径"""
    paths = []
    for path in DEFAULT_DOWNLOAD_PATHS:
        if os.path.exists(path) and os.access(path, os.W_OK):
            paths.append(path)
    return {"paths": paths}

@app.get("/video-info")
async def get_video_info(url: str, request: Request):
    print(f"\n=== Video Info Request ===")
    print(f"Requested URL: {url}")
    
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    ydl_opts = {
        'quiet': False,
        'no_warnings': False,
        'verbose': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        },
        'format': 'best',
        'extract_flat': True,
        'force_generic_extractor': False
    }
    
    try:
        print(f"\nAttempting to fetch video info...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                print("Info extraction successful")
            except Exception as e:
                print(f"Error during extraction: {str(e)}")
                raise HTTPException(status_code=400, detail=f"Failed to extract video info: {str(e)}")
            
            if not info:
                raise HTTPException(status_code=400, detail="No video information found")
            
            print("\nProcessing formats...")
            formats_by_type = {
                'combined': [],  # video+audio formats
                'video': [],     # video-only formats
                'audio': []      # audio-only formats
            }
            
            # 处理所有可用格式
            for f in info.get('formats', []):
                # 获取基本信息
                format_id = f.get('format_id', 'N/A')
                ext = f.get('ext', 'N/A')
                
                # 获取分辨率
                resolution = f.get('resolution', 'N/A')
                if resolution == 'N/A':
                    width = f.get('width', 0)
                    height = f.get('height', 0)
                    if width and height:
                        resolution = f"{width}x{height}"
                
                # 获取编解码器信息
                vcodec = f.get('vcodec', 'none')
                acodec = f.get('acodec', 'none')
                
                # 获取比特率
                vbr = f.get('vbr', 0)
                abr = f.get('abr', 0)
                tbr = f.get('tbr', 0)
                
                # 创建格式对象
                format_info = {
                    'format_id': format_id,
                    'ext': ext,
                    'resolution': resolution,
                    'filesize': humanize.naturalsize(f.get('filesize', 0)),
                    'format_note': f.get('format_note', ''),
                    'fps': f.get('fps', 'N/A'),
                    'vcodec': vcodec.split('.')[0] if vcodec != 'none' else 'N/A',
                    'acodec': acodec.split('.')[0] if acodec != 'none' else 'N/A',
                    'vbr': f"{int(vbr)}kbps" if vbr else "N/A",
                    'abr': f"{int(abr)}kbps" if abr else "N/A",
                    'total_bitrate': f"{int(tbr)}kbps" if tbr else "N/A",
                }
                
                # 根据类型分类
                if vcodec != 'none' and acodec != 'none':
                    format_info['quality_label'] = f"{resolution} ({format_info['total_bitrate']})"
                    formats_by_type['combined'].append(format_info)
                elif vcodec != 'none':
                    format_info['quality_label'] = f"{resolution} ({format_info['vbr']})"
                    formats_by_type['video'].append(format_info)
                elif acodec != 'none':
                    format_info['quality_label'] = f"Audio {format_info['abr']}"
                    formats_by_type['audio'].append(format_info)
            
            # 对每种类型的格式进行排序
            for format_type in formats_by_type:
                if format_type in ['combined', 'video']:
                    # 按分辨率和比特率排序
                    formats_by_type[format_type].sort(key=lambda x: (
                        -int(x['resolution'].split('x')[0]) if 'x' in x['resolution'] else 0,
                        -int(x.get('total_bitrate', '0kbps').replace('kbps', '')) if 'kbps' in x.get('total_bitrate', '') else 0
                    ))
                else:
                    # 音频按比特率排序
                    formats_by_type[format_type].sort(key=lambda x: 
                        -int(x.get('abr', '0kbps').replace('kbps', '')) if 'kbps' in x.get('abr', '') else 0
                    )
            
            if all(len(formats) == 0 for formats in formats_by_type.values()):
                raise HTTPException(status_code=400, detail="No suitable video formats found")
            
            response_data = {
                "title": info.get('title', 'Unknown Title'),
                "duration": str(timedelta(seconds=info.get('duration', 0))),
                "thumbnail": info.get('thumbnail', ''),
                "channel": info.get('channel', 'Unknown Channel'),
                "formats": formats_by_type
            }
            
            print(f"\nSuccess! Video title: {response_data['title']}")
            print(f"Found formats: Combined: {len(formats_by_type['combined'])}, "
                  f"Video: {len(formats_by_type['video'])}, "
                  f"Audio: {len(formats_by_type['audio'])}")
            return response_data
            
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        print("Full error details:", e)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.post("/download")
async def download_video(request: Request):
    try:
        data = await request.json()
        url = data.get('url')
        format_id = data.get('format_id')
        save_path = data.get('save_path')
        
        if not all([url, format_id, save_path]):
            raise HTTPException(status_code=400, detail="Missing required parameters")
            
        ydl_opts = {
            'format': format_id if '+' not in format_id else f'{format_id.split("+")[0]}+bestaudio',
            'merge_output_format': 'mp4',  # 强制合并为mp4格式
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
            'progress_hooks': [lambda d: None],
            'quiet': True,
            'no_warnings': True,
            'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),
            'ffmpeg_location': 'ffmpeg',
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 先获取视频信息
                info = ydl.extract_info(url, download=False)
                print(f"Starting download with format {format_id} to {save_path}")
                asyncio.create_task(download_task(url, ydl_opts, info, save_path))
                
                return JSONResponse({
                    "status": "success",
                    "message": "Download started",
                    "save_path": save_path
                })
                
        except Exception as e:
            print(f"Error starting download: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

async def download_task(url, ydl_opts, info, save_path):
    try:
        print(f"Download started with options: {ydl_opts}")
        
        def progress_hook(d):
            if d['status'] == 'downloading':
                try:
                    total_bytes = d.get('total_bytes', 0)
                    downloaded_bytes = d.get('downloaded_bytes', 0)
                    speed = d.get('speed', 0)
                    eta = d.get('eta', 0)
                    
                    if total_bytes > 0:
                        percent = (downloaded_bytes / total_bytes) * 100
                    else:
                        percent = 0
                        
                    progress_data = {
                        'status': 'downloading',
                        'percent': percent,
                        'speed': speed,
                        'eta': eta
                    }
                    
                    print(f"Progress: {percent}%, Speed: {speed}, ETA: {eta}")
                    # 使用异步循环发送进度信息
                    loop = asyncio.get_event_loop()
                    loop.create_task(manager.broadcast(json.dumps(progress_data)))
                    
                except Exception as e:
                    print(f"Error in progress hook: {str(e)}")
                    print(f"Full error details: {e.__dict__}")
            
            elif d['status'] == 'finished':
                print("Download finished, now converting...")
                # 发送转换状态
                loop = asyncio.get_event_loop()
                loop.create_task(manager.broadcast(json.dumps({
                    'status': 'converting',
                    'message': 'Converting video format...'
                })))
        
        # 添加进度钩子到下载选项
        ydl_opts['progress_hooks'] = [progress_hook]
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # 获取预期的文件名和路径
        filename = f"{info['title']}.mp4"
        filepath = os.path.join(save_path, filename)
        
        # 验证文件是否存在和大小
        if not os.path.exists(filepath):
            original_filename = f"{info['title']}.{info['ext']}"
            filepath = os.path.join(save_path, original_filename)
            if not os.path.exists(filepath):
                raise Exception(f"Download failed: File not found in {save_path}")
        
        filesize = os.path.getsize(filepath)
        if filesize == 0:
            raise Exception(f"Download failed: File is empty (0 bytes)")
        
        print(f"Download completed: {filepath}")
        print(f"File size: {filesize} bytes ({humanize.naturalsize(filesize)})")
        
        # 发送完成消息
        await manager.broadcast(json.dumps({
            "status": "completed",
            "title": info["title"],
            "path": filepath
        }))
        
    except Exception as e:
        print(f"Download error: {str(e)}")
        print(f"Full error details: {e.__dict__}")
        # 发送错误消息
        await manager.broadcast(json.dumps({
            "status": "error",
            "error": str(e)
        }))

@app.get("/videos")
async def get_videos():
    return JSONResponse({"videos": videos}) 

@app.post("/select-folder")
async def select_folder():
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    root.attributes('-topmost', True)  # Make the dialog appear on top
    
    folder_path = filedialog.askdirectory(
        title='Select Download Location',
        mustexist=True  # 确保文件夹存在
    )
    root.destroy()
    
    if not folder_path:
        return {"path": None}
        
    return {"path": folder_path}

@app.post("/open-folder")
async def open_folder(request: Request):
    try:
        data = await request.json()
        folder_path = os.path.dirname(data['path'])
        
        if not os.path.exists(folder_path):
            raise HTTPException(status_code=400, detail="Folder not found")
            
        # 根据操作系统打开文件夹
        system = platform.system()
        try:
            if system == 'Windows':
                os.startfile(folder_path)
            elif system == 'Darwin':  # macOS
                subprocess.run(['open', folder_path])
            else:  # Linux
                subprocess.run(['xdg-open', folder_path])
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to open folder: {str(e)}")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/info")
async def get_video_info(request: Request):
    try:
        data = await request.json()
        url = data.get('url')
        
        if not url:
            raise HTTPException(status_code=400, detail="URL is required")
            
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',  # 使用最佳视频和音频组合
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'format_sort': [
                'res',          # 按分辨率排序
                'fps',          # 然后是帧率
                'codec:h264',   # 优先使用 h264 编码
                'size',         # 然后是文件大小
                'br',           # 最后是比特率
            ]
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # 调试日志：打印所有格式
            print("Available formats:")
            for f in info['formats']:
                print(f"ID: {f['format_id']}, Res: {f.get('height', 'N/A')}p, "
                      f"FPS: {f.get('fps', 'N/A')}, "
                      f"vcodec: {f.get('vcodec', 'none')}, "
                      f"acodec: {f.get('acodec', 'none')}")
            
            # 处理格式信息
            formats = {'combined': [], 'video': [], 'audio': []}
            
            # 处理格式
            for f in info['formats']:
                # 跳过不包含视频或音频的格式
                if f.get('vcodec') == 'none' and f.get('acodec') == 'none':
                    continue

                # 获取最佳音频流
                best_audio = None
                for af in info['formats']:
                    if af.get('vcodec') == 'none' and af.get('acodec') != 'none':
                        if not best_audio or (af.get('filesize', 0) > best_audio.get('filesize', 0)):
                            best_audio = af

                # 处理质量标签
                quality_label = f.get('quality_label', '')
                if not quality_label and f.get('height'):
                    quality_label = f'{f.get("height")}p'
                    if f.get('fps', 0) > 30:
                        quality_label += f' {f.get("fps")}fps'
                elif not quality_label:
                    quality_label = f.get('format_note', 'N/A')

                format_info = {
                    'format_id': f['format_id'],
                    'ext': f['ext'],
                    'quality_label': quality_label,
                    'fps': f.get('fps', 'N/A'),
                    'vcodec': f.get('vcodec', 'N/A'),
                    'acodec': f.get('acodec', 'N/A'),
                    'filesize': humanize.naturalsize(f.get('filesize', 0) or f.get('approximate_filesize', 0)) 
                              if (f.get('filesize') or f.get('approximate_filesize')) else 'N/A',
                    'width': f.get('width', 0),
                    'height': f.get('height', 0)
                }

                # 分类格式
                if f.get('vcodec') != 'none':
                    # 如果是纯视频流，添加音频流ID
                    if f.get('acodec') == 'none' and best_audio:
                        format_info['format_id'] = f'{f["format_id"]}+{best_audio["format_id"]}'
                    formats['combined'].append(format_info)
                elif f.get('acodec') != 'none':
                    formats['audio'].append(format_info)

            # 按分辨率和帧率排序
            for format_type in formats:
                formats[format_type].sort(
                    key=lambda x: (
                        int(x.get('height', 0)) if isinstance(x.get('height'), (int, str)) and str(x.get('height', '')).isdigit() else 0,
                        int(x.get('fps', 0)) if isinstance(x.get('fps'), (int, str)) and str(x.get('fps', '')).isdigit() else 0
                    ),
                    reverse=True
                )

            # 调试日志：打印排序后的格式
            print("\nSorted formats:")
            for format_type, format_list in formats.items():
                print(f"\n{format_type.upper()}:")
                for f in format_list:
                    print(f"Quality: {f['quality_label']}, "
                          f"Height: {f.get('height')}, "
                          f"FPS: {f.get('fps')}")

            return {
                'title': info['title'],
                'duration': str(timedelta(seconds=info['duration'])),
                'thumbnail': info.get('thumbnail', ''),
                'description': info.get('description', ''),
                'formats': formats
            }
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Add this at the bottom of main.py
if __name__ == "__main__":
    import uvicorn
    import os
    
    # 检查必要的目录是否存在
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    
    if not os.path.exists(template_dir):
        print(f"Error: Templates directory not found at {template_dir}")
        print("Creating templates directory...")
        os.makedirs(template_dir)
    
    if not os.path.exists(static_dir):
        print(f"Error: Static directory not found at {static_dir}")
        print("Creating static directory...")
        os.makedirs(static_dir)
    
    if not os.path.exists(os.path.join(template_dir, "index.html")):
        print(f"Error: index.html not found in {template_dir}")
        exit(1)
    
    # Configure the server
    host = "0.0.0.0"  # 允许所有IP访问
    port = 8080  # 换个端口试试
    
    print(f"Starting server at http://{host}:{port}")
    print(f"You can access the website at:")
    print(f"  http://localhost:{port}")
    print(f"  http://127.0.0.1:{port}")
    print("Project directory:", os.path.abspath(os.path.dirname(__file__)))
    print("Templates directory:", template_dir)
    print("Static directory:", static_dir)
    print("Press Ctrl+C to stop the server")
    
    # Start the server
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="debug"
    ) 