# YouTube Video Downloader

一个基于 FastAPI 和 yt-dlp 的 YouTube 视频下载器，提供简洁的 Web 界面，支持多种格式和质量的视频下载。

## 功能特点

- 🎯 支持下载 YouTube 视频和音频
- 📊 实时显示下载进度和速度
- 🎨 美观的用户界面（基于 Tailwind CSS）
- 💾 自定义下载路径
- 🎬 支持多种视频格式和质量选择
- 🔄 WebSocket 实时状态更新
- 📱 响应式设计，支持移动设备

## 预览

![预览图](preview.png)

## 安装要求

- Python 3.7+
- FFmpeg（用于视频处理）

## 快速开始

1. 克隆仓库：
bash
git clone https://github.com/kellyslab/youtube-video-downloader.git
cd youtube-video-downloader

2. 安装依赖：
bash
pip install -r requirements.txt
3. 运行应用：
bash
python main.py
4. 打开浏览器访问：
http://localhost:8080

## 使用说明

1. 在输入框中粘贴 YouTube 视频链接
2. 点击 "Get Info" 获取视频信息
3. 选择保存位置和下载格式
4. 点击 "Download" 开始下载
5. 等待下载完成，可以在下载文件夹中找到视频

## 项目结构
README.md
youtube-video-downloader/
├── main.py # 主应用程序
├── templates/ # HTML 模板
│ └── index.html # 主页面
├── static/ # 静态文件
├── downloads/ # 默认下载目录
├── requirements.txt # 项目依赖
└── README.md # 项目文档

## 主要依赖

- FastAPI: Web 框架
- yt-dlp: YouTube 下载核心
- uvicorn: ASGI 服务器
- Tailwind CSS: UI 样式
- WebSocket: 实时进度更新

## 特性说明

- 支持选择不同视频质量（最高支持 4K）
- 支持下载纯视频或纯音频
- 实时显示下载进度和速度
- 支持自定义下载路径
- 下载完成后可直接打开文件夹
- 响应式设计，支持移动端访问

## 常见问题

1. **无法下载视频？**
   - 确保 URL 正确
   - 检查网络连接
   - 确认视频没有地区限制

2. **下载速度慢？**
   - 检查网络连接
   - 尝试选择较低质量
   - 考虑使用代理

3. **找不到下载的文件？**
   - 检查选择的下载路径
   - 查看是否有写入权限
   - 确认磁盘空间充足

## 贡献指南

欢迎提交 Pull Request 或 Issue！

1. Fork 项目
2. 创建新分支：`git checkout -b feature/AmazingFeature`
3. 提交更改：`git commit -m 'Add some AmazingFeature'`
4. 推送分支：`git push origin feature/AmazingFeature`
5. 提交 Pull Request

## 免责声明

本项目仅供学习和研究使用，视频版权归原作者所有。使用本工具下载视频时，请确保遵守相关法律法规和 YouTube 的服务条款。

## License

[MIT License](LICENSE) © 2024 kellyslab

## 联系方式

- GitHub: [@kellyslab](https://github.com/kellyslab)
