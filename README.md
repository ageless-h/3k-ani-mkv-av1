# 3K动画视频处理系统

这是一个专门用于批量处理动画视频的Python系统，能够将视频转换为AV1编码的MKV格式，提取场景关键帧，压缩为WebP格式，并打包归档。

## 功能特点

- **硬件加速视频转换**: 使用NVIDIA GPU (4090) 进行AV1硬件编码
- **智能场景检测**: 使用PySceneDetect自动检测场景切换点
- **高效图像处理**: 批量调整图像大小并转换为WebP格式
- **分批处理**: 支持大型动画系列的分批处理，避免存储空间不足
- **进度恢复**: 支持中断后从上次位置继续处理
- **完整日志**: 详细的处理日志和错误记录

## 系统要求

### 硬件要求
- NVIDIA GPU (支持AV1编码，如RTX 4090)
- 至少90GB内存
- 至少50GB临时存储空间

### 软件要求
- Linux系统
- Python 3.8+
- FFmpeg (支持av1_nvenc)
- libwebp (用于WebP转换)

## 安装依赖

```bash
# 安装Python依赖
pip install -r requirements.txt

# 确保FFmpeg支持AV1硬件编码
ffmpeg -encoders | grep av1_nvenc

# 下载libwebp并放置到项目目录
# 将libwebp二进制文件放置到 ./libwebp/bin/cwebp
```

## 配置

编辑 `config.py` 文件中的路径和参数：

```python
# 主要路径配置
SOURCE_DIR = "/volume1/db/5_video/archive"          # 源视频目录
OUTPUT_DIR = "/volume1/db/1_ai/data/image/animation" # 输出归档目录
VIDEO_OUTPUT_DIR = "/volume1/db/1_ai/data/video/animation" # 转换后视频目录
FILELIST_PATH = "/root/3k-animation-mkv-av1/code/filelist.txt" # 视频列表文件

# 处理参数
MAX_EPISODES_PER_BATCH = 30  # 每批处理的最大集数
MAX_IMAGE_SIZE = 2048        # 图像最大尺寸
WEBP_QUALITY = 90           # WebP质量
```

## 使用方法

### 1. 准备视频文件列表（可选）

如果有预先准备的视频文件列表，将其放置到 `FILELIST_PATH` 指定的位置：

```bash
# 示例文件内容
/volume1/db/5_video/archive/动画A/第01集.mkv
/volume1/db/5_video/archive/动画A/第02集.mkv
/volume1/db/5_video/archive/动画B/S01E01.mp4
```

### 2. 运行处理程序

```bash
python main.py
```

### 3. 监控处理进度

程序会在 `/tmp/animation_processing/` 目录下创建日志文件：

```bash
# 查看实时日志
tail -f /tmp/animation_processing/animation_processor.log

# 查看进度文件
cat /tmp/animation_processing/progress.json
```

## 处理流程

1. **视频组织**: 按源目录的一级子文件夹分组动画系列
2. **批次规划**: 根据集数决定单批次或多批次处理策略
3. **视频处理**: 
   - 场景检测和关键帧提取
   - 图像调整大小（最大2048x2048）
   - WebP格式转换（90%质量）
4. **文件命名**: 按系列重新编号（000001.webp, 000002.webp...）
5. **归档打包**: 创建tar.gz压缩包
6. **清理工作**: 删除临时文件，释放空间

## 输出格式

### 单系列（≤30集）
```
动画名称.tar.gz
```

### 多系列（>30集）
```
动画名称_part01of05.tar.gz
动画名称_part02of05.tar.gz
...
```

## 错误处理

- **磁盘空间不足**: 程序会自动监控空间，不足时暂停处理
- **视频损坏**: 跳过无法处理的视频文件
- **处理中断**: 支持从上次中断位置继续处理
- **硬件错误**: 自动回退到软件处理方案

## 注意事项

1. **存储空间**: 确保有足够的临时存储空间（建议至少50GB）
2. **网络连接**: 确保NAS网络连接稳定
3. **定期清理**: 处理完成后会自动清理临时文件
4. **备份重要**: 建议在处理前备份重要视频文件

## 故障排除

### 常见问题

1. **FFmpeg AV1编码错误**
   ```bash
   # 检查GPU支持
   nvidia-smi
   ffmpeg -encoders | grep av1_nvenc
   ```

2. **WebP转换失败**
   ```bash
   # 检查libwebp路径
   ls -la ./libwebp/bin/cwebp
   ./libwebp/bin/cwebp -version
   ```

3. **磁盘空间问题**
   ```bash
   # 检查磁盘使用情况
   df -h
   du -sh /tmp/animation_processing/
   ```

## 性能优化

- 根据实际硬件调整 `MAX_WORKERS` 参数
- 根据磁盘性能调整 `MAX_EPISODES_PER_BATCH`
- 根据质量要求调整 `WEBP_QUALITY`

## 日志级别

- `INFO`: 主要处理步骤
- `DEBUG`: 详细处理信息
- `WARNING`: 非致命错误
- `ERROR`: 严重错误

查看特定级别的日志：
```bash
grep "ERROR" /tmp/animation_processing/animation_processor.log
``` 