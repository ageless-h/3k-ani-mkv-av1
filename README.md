# 3K Animation MKV-AV1 Processing System (魔搭社区版)

一个专业的动画视频处理系统，基于魔搭社区进行数据管理，将动画视频转换为 MKV+AV1 格式，并提取场景帧制作成 WebP 图像归档。

## 🎯 功能特性

- **☁️ 云端数据流**: 基于魔搭社区的视频下载和结果上传
- **🎬 视频转换**: 批量转换动画视频为 MKV+AV1 格式，支持 NVIDIA GPU 硬件加速
- **🎭 场景检测**: 使用 PySceneDetect 提取每个场景的中间帧
- **🖼️ 图像处理**: 自动调整图像尺寸并转换为 WebP 格式（90% 质量）
- **📦 智能归档**: 按动画系列自动组织和打包图像为 tar.gz 归档
- **🔄 自动监控**: 实时监控魔搭仓库，文件夹上传完成后自动处理
- **⚡ 智能队列**: 小文件夹优先处理，提高响应速度
- **🛡️ 恢复功能**: 支持中断后从上次进度继续处理

## 🔗 魔搭仓库

- **输入仓库**: [ageless/3k-animation-mkv-av1](https://www.modelscope.cn/datasets/ageless/3k-animation-mkv-av1)
- **MKV输出**: [ageless/3k-animation-mkv-av1-output](https://www.modelscope.cn/datasets/ageless/3k-animation-mkv-av1-output)
- **WebP输出**: [ageless/3k-animation-mkv-av1-output-webp](https://www.modelscope.cn/datasets/ageless/3k-animation-mkv-av1-output-webp)

## 📁 项目结构

```
3k-animation-mkv-av1/
├── src/                         # 源代码
│   ├── __init__.py             # 包初始化
│   ├── main.py                 # 主程序入口
│   ├── modelscope_manager.py   # 魔搭社区数据管理
│   ├── video_processor.py      # 视频处理模块
│   ├── image_processor.py      # 图像处理模块
│   ├── archive_manager.py      # 归档管理模块
│   └── utils.py                # 工具函数
├── config/                      # 配置文件
│   ├── config.py               # 主配置文件
│   └── modelscope_config.py    # 魔搭专用配置
├── tools/                       # 工具脚本
│   ├── modelscope_monitor.py   # 魔搭仓库监控器
│   ├── queue_processor.py      # 队列处理器
│   ├── check_environment.py    # 环境检查
│   └── install_libwebp.sh      # WebP库安装
├── doc/                         # 文档
│   ├── upload.py               # 上传工具
│   ├── 魔搭使用指南.md          # 魔搭使用文档
│   └── 自动监控使用指南.md       # 监控系统文档
├── log/                         # 日志目录
├── run.sh                       # 运行脚本
├── start_monitoring.sh          # 监控启动脚本
├── deploy.py                    # 一键部署脚本
└── requirements.txt             # Python依赖
```

## 🚀 快速开始

### 1. 环境要求

- **Python**: 3.8+
- **FFmpeg**: 支持 AV1 硬件编码
- **GPU**: NVIDIA RTX 系列（用于硬件加速）
- **系统**: Linux (推荐 Ubuntu 20.04+)
- **磁盘空间**: 至少 50GB 临时空间

### 2. 一键部署

```bash
# 克隆项目
git clone https://github.com/ageless-h/3k-ani-mkv-av1.git
cd 3k-animation-mkv-av1

# 一键部署
python3 deploy.py

# 启动自动监控（推荐）
bash start_monitoring.sh

# 或手动运行
bash run.sh
```

### 3. 依赖安装

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装系统依赖
sudo apt update
sudo apt install ffmpeg

# 安装 libwebp（可选，用于高性能 WebP 转换）
bash tools/install_libwebp.sh
```

## 🎮 使用方式

### 自动监控模式（推荐）

```bash
# 启动监控系统
bash start_monitoring.sh

# 查看队列状态
python3 tools/queue_processor.py --status

# 查看监控器状态
python3 tools/modelscope_monitor.py --queue
```

### 手动处理模式

```bash
# 运行单次处理
bash run.sh

# 只检查一次仓库
python3 tools/modelscope_monitor.py --once
```

### 管理命令

```bash
# 查看处理日志
tail -f log/processing.log

# 停止监控系统
tmux kill-session -t animation_monitor

# 手动上传文件
python3 doc/upload.py file --path /path/to/file --repo output_webp
```

## ⚙️ 配置说明

### 主配置文件 (`config/config.py`)

```python
class Config:
    # 部署模式
    DEPLOYMENT_MODE = "modelscope"
    
    # 魔搭社区Token
    MODELSCOPE_TOKEN = "ms-30a739b2-842b-4fe7-8485-ab9b5114afb5"
    
    # 处理参数
    MAX_EPISODES_PER_BATCH = 30     # 每批处理的视频数量
    MIN_FREE_SPACE_GB = 10          # 最小保留磁盘空间
    
    # FFmpeg AV1 编码参数
    FFMPEG_AV1_PARAMS = [
        "-c:v", "av1_nvenc",        # NVIDIA硬件编码
        "-preset", "p7",            # 最高质量
        "-crf", "23"                # 质量控制
    ]
```

### 监控配置

```python
# 监控器设置
monitor_interval = 300              # 5分钟检查一次
min_folder_stable_time = 600        # 10分钟稳定才认为完成

# 处理器设置  
check_interval = 60                 # 1分钟检查一次队列
max_concurrent = 1                  # 最大并发处理数
```

## 🔍 工作流程

1. **📡 监控阶段**: 每5分钟检查魔搭输入仓库的更新
2. **🧠 检测完成**: 文件夹10分钟内无变化认为上传完成
3. **⚡ 加入队列**: 完成的文件夹按优先级加入处理队列
4. **📥 下载处理**: 从魔搭仓库下载视频到本地临时目录
5. **🎬 视频转换**: 转换为MKV+AV1格式，使用NVIDIA硬件加速
6. **🎭 场景检测**: 使用PySceneDetect识别场景并提取中间帧
7. **🖼️ 图像处理**: 调整尺寸并转换为WebP格式
8. **📦 创建归档**: 生成tar.gz压缩包
9. **📤 上传结果**: 分别上传MKV和WebP结果到对应仓库
10. **🧹 清理临时**: 删除本地临时文件，释放空间

## 📊 核心模块

- **`ModelScopeManager`**: 魔搭社区数据管理，处理上传下载
- **`VideoProcessor`**: 视频转换和场景检测
- **`ImageProcessor`**: 图像处理和WebP转换
- **`ArchiveManager`**: 文件归档和压缩
- **`ModelScopeMonitor`**: 仓库监控和队列管理
- **`QueueProcessor`**: 队列处理和任务调度

## 🛠️ 故障排除

### 常见问题

1. **魔搭登录失败**
   ```bash
   modelscope login --token ms-30a739b2-842b-4fe7-8485-ab9b5114afb5
   ```

2. **GPU编码失败**
   ```bash
   # 检查NVIDIA驱动
   nvidia-smi
   
   # 检查FFmpeg AV1支持
   ffmpeg -encoders | grep av1
   ```

3. **磁盘空间不足**
   ```bash
   # 清理临时文件
   rm -rf /tmp/modelscope_*
   rm -rf /tmp/animation_*
   ```

4. **队列堆积**
   ```bash
   # 增加并发数
   python3 tools/queue_processor.py --concurrent 2
   ```

### 性能优化

- **调整批次大小**: 根据GPU内存调整 `MAX_EPISODES_PER_BATCH`
- **并发处理**: 增加 `max_concurrent` 提高吞吐量
- **存储优化**: 使用SSD存储临时文件
- **网络优化**: 调整上传下载并发数

## 📈 监控指标

- **处理速度**: 约每小时处理20-50个视频（取决于长度和复杂度）
- **压缩比**: WebP图像相比PNG节省60-80%空间
- **AV1压缩**: 相比H.264节省30-50%文件大小
- **检测延迟**: 最多15分钟（5分钟检查间隔 + 10分钟稳定时间）

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- **魔搭社区**: 提供优秀的数据集托管服务
- **PySceneDetect**: 强大的场景检测库
- **FFmpeg**: 多媒体处理的瑞士军刀
- **NVIDIA**: 提供AV1硬件编码支持

---

## 📞 支持

- **项目仓库**: https://github.com/ageless-h/3k-ani-mkv-av1
- **问题反馈**: [GitHub Issues](https://github.com/ageless-h/3k-ani-mkv-av1/issues)
- **功能请求**: [GitHub Discussions](https://github.com/ageless-h/3k-ani-mkv-av1/discussions)

**让我们一起打造更好的动画处理工具！** 🎬✨ 