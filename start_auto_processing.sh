#!/bin/bash
# 3K Animation MKV-AV1 Processing System - 一键自动处理启动脚本
# 模式：立即处理现有数据 + 持续监控新数据

echo "🚀 3K动画视频处理系统 - 自动处理模式"
echo "========================================"
echo "📋 处理策略："
echo "   1. 立即扫描魔搭仓库现有数据并加入队列"
echo "   2. 开始处理现有数据"
echo "   3. 同时监控新上传的数据"
echo "========================================"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 检查依赖包
echo "🔍 检查依赖包..."
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
echo "🎬 启动自动处理系统"
echo "========================================"

# 使用tmux启动系统
if command -v tmux &> /dev/null; then
    echo "📡 使用tmux启动自动处理系统..."
    
    # 创建tmux会话
    tmux new-session -d -s animation_auto
    
    # 启动监控器（自动模式：先初始化再监控）
    tmux send-keys -t animation_auto "python3 tools/modelscope_monitor.py --auto" Enter
    
    # 等待3秒，让监控器完成初始化
    sleep 3
    
    # 创建新窗口启动处理器
    tmux new-window -t animation_auto -n processor
    tmux send-keys -t animation_auto:processor "python3 tools/queue_processor.py" Enter
    
    echo "✅ 自动处理系统已启动!"
    echo ""
    echo "📋 管理命令:"
    echo "  查看监控器: tmux attach -t animation_auto:0"
    echo "  查看处理器: tmux attach -t animation_auto:processor"
    echo "  查看队列状态: python3 tools/queue_processor.py --status"
    echo "  停止系统: tmux kill-session -t animation_auto"
    echo ""
    echo "🔍 实时监控:"
    echo "  tail -f log/processing.log"
    echo ""
    echo "📊 初始化状态:"
    # 等待一下让系统初始化完成
    sleep 2
    python3 tools/queue_processor.py --status
    
    # 显示tmux会话信息
    echo ""
    echo "📺 活动会话:"
    tmux list-sessions | grep animation_auto
    
else
    echo "⚠️  未安装tmux，将在前台运行"
    echo "💡 建议安装tmux: sudo apt install tmux"
    echo ""
    
    # 步骤1：初始化队列
    echo "📋 步骤1: 初始化处理队列..."
    python3 tools/modelscope_monitor.py --init
    
    if [ $? -ne 0 ]; then
        echo "❌ 初始化失败"
        exit 1
    fi
    
    # 步骤2：在后台启动处理器
    echo "🔄 步骤2: 启动队列处理器..."
    python3 tools/queue_processor.py &
    PROCESSOR_PID=$!
    echo "处理器PID: $PROCESSOR_PID"
    
    # 步骤3：前台运行监控器
    echo "📡 步骤3: 启动仓库监控器..."
    python3 tools/modelscope_monitor.py
    
    # 清理后台进程
    echo "🛑 停止处理器..."
    kill $PROCESSOR_PID 2>/dev/null
fi

echo "========================================"
echo "🎉 自动处理系统已停止" 