#!/bin/bash

# 3K Animation MKV-AV1 Processing System (魔搭社区版)
# 启动脚本

echo "🎬 3K动画视频处理系统 (魔搭社区版)"
echo "=================================="

# 检查Python环境
echo "检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 检查虚拟环境
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  建议在虚拟环境中运行"
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

# 检查工具依赖
echo "检查系统环境..."
python3 tools/check_environment.py

# 运行环境检查
if [ $? -ne 0 ]; then
    echo "⚠️  环境检查发现问题，但程序将继续运行"
fi

# 创建日志目录
mkdir -p log

# 启动主程序
echo "启动主程序..."
echo "=================================="

# 添加项目根目录到Python路径
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 运行主程序
python3 -c "
import sys
sys.path.insert(0, '.')
from src.main import main
main()
"

echo "=================================="
echo "处理完成！" 