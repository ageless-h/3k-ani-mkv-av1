#!/bin/bash

# 3K动画视频处理系统启动脚本

echo "=== 3K动画视频处理系统 ==="
echo "开始检查系统环境..."

# 检查Python版本
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到python3"
    exit 1
fi

echo "Python版本: $(python3 --version)"

# 检查FFmpeg和AV1支持
if ! command -v ffmpeg &> /dev/null; then
    echo "错误: 未找到ffmpeg"
    exit 1
fi

echo "FFmpeg版本: $(ffmpeg -version | head -n 1)"

# 检查AV1硬件编码支持
if ! ffmpeg -encoders 2>/dev/null | grep -q av1_nvenc; then
    echo "警告: 未检测到AV1硬件编码支持(av1_nvenc)"
    echo "将使用软件编码，速度会较慢"
fi

# 检查GPU
if command -v nvidia-smi &> /dev/null; then
    echo "GPU状态:"
    nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits
else
    echo "警告: 未检测到NVIDIA GPU"
fi

# 检查磁盘空间
echo "磁盘空间检查:"
df -h / | tail -n 1
df -h /tmp | tail -n 1

# 检查libwebp
if [ -f "./libwebp/bin/cwebp" ]; then
    echo "libwebp: 已找到"
    ./libwebp/bin/cwebp -version 2>/dev/null || echo "libwebp版本检查失败"
else
    echo "警告: 未找到libwebp，将使用Pillow备用方案"
fi

# 检查依赖
echo "检查Python依赖..."
if ! python3 -c "import cv2, scenedetect, PIL, numpy, tqdm" 2>/dev/null; then
    echo "安装Python依赖..."
    pip3 install -r requirements.txt
fi

echo ""
echo "环境检查完成！"
echo "开始处理动画视频..."
echo ""

# 运行主程序
python3 main.py

echo ""
echo "处理完成！" 