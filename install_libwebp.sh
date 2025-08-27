#!/bin/bash

# libwebp安装脚本
# 用于在Linux服务器上安装libwebp工具

echo "🔧 开始安装libwebp..."

# 创建临时目录
TEMP_DIR="/tmp/libwebp_install"
mkdir -p $TEMP_DIR
cd $TEMP_DIR

# 检测系统架构
ARCH=$(uname -m)
echo "检测到系统架构: $ARCH"

# 根据架构选择下载链接
if [ "$ARCH" = "x86_64" ]; then
    WEBP_URL="https://storage.googleapis.com/downloads.webmproject.org/releases/webp/libwebp-1.3.2-linux-x86-64.tar.gz"
    WEBP_FILE="libwebp-1.3.2-linux-x86-64.tar.gz"
    WEBP_DIR="libwebp-1.3.2-linux-x86-64"
elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    echo "⚠️  ARM64架构，尝试使用包管理器安装..."
    
    # 尝试使用包管理器安装
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y webp
        if [ $? -eq 0 ]; then
            echo "✅ libwebp通过apt安装成功"
            exit 0
        fi
    elif command -v yum &> /dev/null; then
        sudo yum install -y libwebp-tools
        if [ $? -eq 0 ]; then
            echo "✅ libwebp通过yum安装成功"
            exit 0
        fi
    fi
    
    echo "❌ 无法自动安装libwebp，将使用Pillow备用方案"
    exit 1
else
    echo "❌ 不支持的架构: $ARCH"
    exit 1
fi

# 下载libwebp
echo "📥 下载libwebp..."
if command -v wget &> /dev/null; then
    wget $WEBP_URL
elif command -v curl &> /dev/null; then
    curl -O $WEBP_URL
else
    echo "❌ 需要wget或curl来下载文件"
    exit 1
fi

# 检查下载是否成功
if [ ! -f "$WEBP_FILE" ]; then
    echo "❌ 下载失败"
    exit 1
fi

# 解压
echo "📦 解压libwebp..."
tar -xzf $WEBP_FILE

if [ ! -d "$WEBP_DIR" ]; then
    echo "❌ 解压失败"
    exit 1
fi

# 复制到项目目录
PROJECT_DIR="/root/3k-ani-mkv-av1"
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ 项目目录不存在: $PROJECT_DIR"
    exit 1
fi

echo "📁 复制到项目目录..."
mkdir -p $PROJECT_DIR/libwebp/bin
cp $WEBP_DIR/bin/cwebp $PROJECT_DIR/libwebp/bin/
cp $WEBP_DIR/bin/dwebp $PROJECT_DIR/libwebp/bin/

# 设置可执行权限
chmod +x $PROJECT_DIR/libwebp/bin/*

# 测试安装
echo "🧪 测试libwebp安装..."
if $PROJECT_DIR/libwebp/bin/cwebp -version &> /dev/null; then
    echo "✅ libwebp安装成功!"
    $PROJECT_DIR/libwebp/bin/cwebp -version
else
    echo "❌ libwebp测试失败"
    exit 1
fi

# 清理临时文件
cd /
rm -rf $TEMP_DIR

echo "🎉 libwebp安装完成!"
echo "现在可以运行: python check_environment.py 来验证安装" 