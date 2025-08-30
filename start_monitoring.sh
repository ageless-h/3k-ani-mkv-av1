#!/bin/bash
# 3K Animation MKV-AV1 Processing System - 监控模式启动脚本

echo "🎬 3K动画视频处理系统 - 自动监控模式"
echo "========================================"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 检查依赖包
echo "检查依赖包..."
python3 -c "import cv2, scenedetect, PIL, numpy, tqdm, modelscope" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ 缺少必要的依赖包，请运行: pip install -r requirements.txt"
    exit 1
fi

# 检查配置文件
if [ ! -f "config/config.py" ]; then
    echo "❌ 配置文件不存在，魔搭模式应该有默认配置"
    echo "请检查config/config.py是否存在，或运行 python3 deploy.py 重新部署"
    exit 1
fi

# 检查魔搭登录状态
echo "🔐 检查魔搭社区登录状态..."
modelscope login --token ms-30a739b2-842b-4fe7-8485-ab9b5114afb5

if [ $? -ne 0 ]; then
    echo "❌ 魔搭社区登录失败，请检查token"
    exit 1
fi

echo "✅ 魔搭社区连接正常"

# 创建日志目录
mkdir -p log

# 添加项目根目录到Python路径
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

echo "========================================"
echo "🚀 启动自动监控处理系统"
echo "========================================"

# 使用tmux启动两个进程
if command -v tmux &> /dev/null; then
    echo "📡 使用tmux启动监控器和处理器..."
    
    # 创建tmux会话
    tmux new-session -d -s animation_monitor
    
    # 启动监控器
    tmux send-keys -t animation_monitor "python3 tools/modelscope_monitor.py" Enter
    
    # 创建新窗口启动处理器
    tmux new-window -t animation_monitor -n processor
    tmux send-keys -t animation_monitor:processor "python3 tools/queue_processor.py" Enter
    
    echo "✅ 监控系统已启动!"
    echo ""
    echo "📋 管理命令:"
    echo "  查看监控器: tmux attach -t animation_monitor:0"
    echo "  查看处理器: tmux attach -t animation_monitor:processor"
    echo "  查看队列状态: python3 tools/queue_processor.py --status"
    echo "  停止系统: tmux kill-session -t animation_monitor"
    echo ""
    echo "🔍 实时日志:"
    echo "  tail -f log/processing.log"
    
    # 显示tmux会话信息
    tmux list-sessions | grep animation_monitor
    
else
    echo "⚠️  未安装tmux，将在前台运行监控器"
    echo "💡 建议安装tmux: sudo apt install tmux"
    echo ""
    
    # 在后台启动处理器
    echo "🔄 启动队列处理器..."
    python3 tools/queue_processor.py &
    PROCESSOR_PID=$!
    echo "处理器PID: $PROCESSOR_PID"
    
    # 前台运行监控器
    echo "📡 启动仓库监控器..."
    python3 tools/modelscope_monitor.py
    
    # 清理后台进程
    echo "🛑 停止处理器..."
    kill $PROCESSOR_PID 2>/dev/null
fi

echo "========================================"
echo "🎉 监控系统已停止" 