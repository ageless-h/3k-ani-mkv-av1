# 3K Animation MKV-AV1 Processing System

一个专业的动画视频处理系统，将动画视频转换为 MKV+AV1 格式，并提取场景帧制作成 WebP 图像归档。

## 🎯 功能特性

- **视频转换**: 批量转换动画视频为 MKV+AV1 格式，支持 NVIDIA GPU 硬件加速
- **场景检测**: 使用 PySceneDetect 提取每个场景的中间帧
- **图像处理**: 自动调整图像尺寸并转换为 WebP 格式（90% 质量）
- **智能归档**: 按动画系列自动组织和打包图像为 tar.gz 归档
- **网络传输**: 通过 Tailscale 网络连接 NAS 进行文件传输
- **批处理**: 支持大型动画系列的分批处理
- **恢复功能**: 支持中断后从上次进度继续处理

## 📁 项目结构

```
3k-animation-mkv-av1/
├── src/                    # 源代码
│   ├── __init__.py        # 包初始化
│   ├── main.py            # 主程序入口
│   ├── video_processor.py # 视频处理模块
│   ├── image_processor.py # 图像处理模块
│   ├── archive_manager.py # 归档管理模块
│   ├── network_utils.py   # 网络连接工具
│   └── utils.py           # 通用工具函数
├── config/                # 配置文件
│   ├── config.py          # 主配置文件
│   └── config_example.py  # 配置模板
├── tools/                 # 工具脚本
│   ├── check_environment.py    # 环境检查
│   ├── diagnose_nas.py         # NAS连接诊断
│   ├── ugreen_nas_config.py    # 绿联云配置检测
│   └── install_libwebp.sh      # libwebp安装脚本
├── doc/                   # 文档
│   ├── README.md          # 项目说明
│   ├── 部署指南.md        # 部署指南
│   ├── 绿联云SSH启用指南.md # SSH配置指南
│   └── fix_nas_ssh.md     # SSH问题修复
├── log/                   # 日志文件
├── requirements.txt       # Python依赖
└── run.sh                # 启动脚本
```

## 🚀 快速开始

### 1. 环境要求

- **操作系统**: Linux (推荐 Ubuntu 20.04+)
- **Python**: 3.8+
- **GPU**: NVIDIA RTX 4090 (支持 AV1 硬件编码)
- **网络**: Tailscale VPN 连接
- **存储**: 至少 50GB 临时空间

### 2. 安装依赖

```bash
# 克隆项目
git clone https://github.com/ageless-h/3k-ani-mkv-av1.git
cd 3k-animation-mkv-av1

# 安装Python依赖
pip install -r requirements.txt

# 安装libwebp (可选，提升WebP压缩性能)
bash tools/install_libwebp.sh
```

### 3. 配置系统

```bash
# 复制配置模板
cp config/config_example.py config/config.py

# 根据你的环境修改配置
vim config/config.py

# 或使用自动配置工具 (适用于绿联云用户)
python3 tools/ugreen_nas_config.py
```

### 4. 环境检查

```bash
# 检查系统环境
python3 tools/check_environment.py

# 检查NAS连接
python3 tools/diagnose_nas.py
```

### 5. 运行程序

```bash
# 使用启动脚本 (推荐)
bash run.sh

# 或直接运行
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python3 -c "from src.main import main; main()"
```

## ⚙️ 配置说明

主要配置项目在 `config/config.py` 中：

```python
class Config:
    # NAS连接配置
    NAS_IP = "100.74.107.59"        # NAS IP地址
    SSH_USER = "root"               # SSH用户名
    SSH_PORT = 22                   # SSH端口
    
    # 路径配置
    SOURCE_DIR = "/volume1/db/5_video/archive"    # NAS源视频目录
    OUTPUT_DIR = "/root/output/animation"         # 本地输出目录
    TEMP_DIR = "/tmp/animation_processing"        # 临时目录
    
    # 处理参数
    MAX_EPISODES_PER_BATCH = 30     # 每批最大集数
    MAX_WORKERS = 4                 # 并发工作线程
    WEBP_QUALITY = 90              # WebP质量
    TARGET_SIZE = 2048             # 图像目标尺寸
```

## 🔧 工具脚本

- **`tools/check_environment.py`**: 全面的环境检查工具
- **`tools/diagnose_nas.py`**: NAS网络连接诊断
- **`tools/ugreen_nas_config.py`**: 绿联云NAS自动配置
- **`tools/install_libwebp.sh`**: 自动安装libwebp工具

## 📊 性能优化

- **GPU加速**: 自动使用 NVIDIA RTX 4090 进行 AV1 硬件编码
- **并发处理**: 支持多线程并发处理提升效率
- **智能缓存**: 本地缓存机制减少网络传输
- **分批处理**: 大型系列自动分批避免内存溢出

## 🐛 故障排除

### 网络连接问题
```bash
# 检查Tailscale状态
tailscale status

# 诊断NAS连接
python3 tools/diagnose_nas.py
```

### GPU编码问题
```bash
# 检查GPU状态
nvidia-smi

# 检查AV1编码支持
ffmpeg -encoders | grep av1_nvenc
```

### 权限问题
```bash
# 检查SSH密钥
ssh-copy-id root@100.74.107.59

# 检查文件权限
ls -la /tmp/animation_processing
```

## 📝 开发

项目采用模块化设计，主要模块：

- **`src/main.py`**: 主程序逻辑和工作流编排
- **`src/video_processor.py`**: 视频转换和场景检测
- **`src/image_processor.py`**: 图像处理和WebP转换
- **`src/archive_manager.py`**: 文件归档和压缩管理
- **`src/network_utils.py`**: NAS网络连接和文件传输
- **`src/utils.py`**: 通用工具函数

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**作者**: ageless-h  
**项目**: https://github.com/ageless-h/3k-ani-mkv-av1.git 