# 🎬 简化视频处理系统 (MKV+AV1)

一个专门用于批量处理动画视频的简化系统，实现单文件 MP4→MKV+AV1 转换流水线。

## 🎯 功能特性

- **单文件处理流水线** - 发现一个视频处理一个，无需等待完整文件夹
- **保留原文件名前缀** - `动画名 - 0001.mp4` → `动画名 - 0001.mkv`
- **MKV+AV1硬件编码** - 使用NVIDIA `av1_nvenc`进行高效压缩
- **ModelScope集成** - 自动从仓库下载，处理后上传回仓库
- **实时监控** - 持续监控新上传的视频文件
- **断点续传** - 记录处理状态，支持中断后继续
- **批量处理** - 支持处理数万个视频文件

## 🏗️ 系统架构

```
📁 视频仓库监控 → 📥 单文件下载 → 🔄 MKV+AV1转换 → 📤 上传结果 → ✅ 标记完成
```

### 核心组件

- **`simple_run.py`** - 主程序，集成监控和处理功能
- **`src/simple_processor.py`** - 简化的视频转换器
- **`tools/simple_monitor.py`** - 视频文件监控器
- **`tools/simple_processor.py`** - 完整处理流程工作器
- **`simple_start.sh`** - 启动脚本

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 检查环境

确保已安装：
- Python 3.8+
- FFmpeg (支持 av1_nvenc)
- NVIDIA GPU 驱动

### 3. 配置Token

确保 `config/config.py` 中的 ModelScope token 正确配置。

### 4. 启动系统

```bash
# 使用启动脚本（推荐）
bash simple_start.sh

# 或直接运行Python
python simple_run.py
```

## 📋 使用模式

### 完整模式
处理现有所有视频 + 持续监控新视频
```bash
python simple_run.py
```

### 仅监控新视频
跳过现有视频，只处理新上传的
```bash
python simple_run.py --no-init
```

### 仅初始化队列
扫描现有视频并添加到队列，但不开始处理
```bash
python simple_run.py --init-only
```

### 查看状态
显示当前队列和处理进度
```bash
python simple_run.py --status
```

## 🔧 工作流程

### 视频处理流程
1. **队列扫描** - 从 ModelScope 仓库或 `filelist.txt` 获取视频列表
2. **单文件下载** - 使用 `modelscope download` 下载单个视频
3. **格式转换** - FFmpeg MKV+AV1 硬件编码
4. **上传结果** - 使用 `modelscope upload` 上传转换后的文件
5. **状态更新** - 标记为已处理，从队列移除

### 文件命名规则
- **输入**: `系列名/系列名 - 0001.mp4`
- **输出**: `系列名/系列名 - 0001.mkv`
- **保持目录结构不变**

## 📊 系统状态

系统会处理检测到的所有视频文件，包括：
- 从 ModelScope 仓库实时下载的视频
- 从 `filelist.txt` 读取的视频列表
- 新上传到仓库的视频文件

处理进度和状态保存在：
- `log/monitor_state.json` - 已处理视频记录
- `log/video_queue.json` - 待处理队列
- `log/` - 详细日志文件

## ⚙️ 配置说明

### FFmpeg 参数
- **编码器**: `av1_nvenc` (NVIDIA硬件编码)
- **预设**: `p4` (平衡质量和速度)
- **质量控制**: CQ 28
- **音频/字幕**: 直接复制

### 监控设置
- **检查间隔**: 5分钟
- **下载超时**: 30分钟
- **转换超时**: 1小时

## 🛠️ 故障排除

### 常见问题

1. **ModelScope登录失败**
   - 检查token是否正确
   - 确认网络连接正常

2. **FFmpeg转换失败**
   - 确认GPU驱动支持AV1编码
   - 检查显存是否足够

3. **下载超时**
   - 增加超时时间
   - 检查网络稳定性

### 日志查看
```bash
tail -f log/simple_system_*.log
```

## 📁 项目结构

```
3k-animation-mkv-av1/
├── simple_run.py              # 主程序
├── simple_start.sh            # 启动脚本  
├── filelist.txt               # 视频文件列表
├── config/
│   ├── config.py              # 主配置
│   └── modelscope_config.py   # ModelScope配置
├── src/
│   ├── simple_processor.py    # 视频转换器
│   ├── modelscope_manager.py  # ModelScope管理器
│   └── utils.py               # 工具函数
├── tools/
│   ├── simple_monitor.py      # 视频监控器
│   └── simple_processor.py    # 处理工作器
└── log/                       # 日志和状态文件
```

## 📝 许可证

MIT License

## 🔗 相关链接

- [ModelScope平台](https://modelscope.cn/)
- [FFmpeg官网](https://ffmpeg.org/)
- [AV1编码规范](https://aomedia.org/) 