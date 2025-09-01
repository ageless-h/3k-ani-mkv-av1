#!/bin/bash
# -*- coding: utf-8 -*-
# 简化视频处理系统启动脚本

echo "🎬 简化视频处理系统 (MKV+AV1)"
echo "========================================"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 检查必要的包
echo "🔍 检查依赖..."
python3 -c "import modelscope" 2>/dev/null || {
    echo "❌ modelscope 未安装，请运行: pip install modelscope"
    exit 1
}

# 检查FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ FFmpeg 未安装"
    exit 1
fi

# 检查配置文件
if [ ! -f "config/config.py" ]; then
    echo "❌ 配置文件不存在"
    exit 1
fi

echo "✅ 环境检查通过"
echo ""

# 显示选项
echo "请选择运行模式："
echo "1. 完整模式 (初始化+监控+处理)"
echo "2. 仅处理新视频 (跳过初始化)"
echo "3. 仅初始化队列"
echo "4. 查看状态"
echo ""

read -p "请输入选择 (1-4): " choice

case $choice in
    1)
        echo "🚀 启动完整模式..."
        python3 simple_run.py
        ;;
    2)
        echo "🚀 启动新视频处理模式..."
        python3 simple_run.py --no-init
        ;;
    3)
        echo "🚀 初始化队列..."
        python3 simple_run.py --init-only
        ;;
    4)
        echo "📊 查看系统状态..."
        python3 simple_run.py --status
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac 