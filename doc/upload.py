#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
魔搭社区上传工具
用于快速上传文件到魔搭数据集仓库
"""

import os
import sys
import argparse
from pathlib import Path

try:
    from modelscope.hub.api import HubApi
    MODELSCOPE_AVAILABLE = True
except ImportError:
    MODELSCOPE_AVAILABLE = False

# 默认配置
DEFAULT_TOKEN = "ms-30a739b2-842b-4fe7-8485-ab9b5114afb5"
REPOSITORIES = {
    'input': 'ageless/3k-animation-mkv-av1',
    'output_mkv': 'ageless/3k-animation-mkv-av1-output',
    'output_webp': 'ageless/3k-animation-mkv-av1-output-webp'
}

def upload_file(file_path: str, repo_type: str, remote_path: str = None, token: str = None):
    """
    上传单个文件到魔搭仓库
    
    Args:
        file_path: 本地文件路径
        repo_type: 仓库类型 (input/output_mkv/output_webp)
        remote_path: 远程路径（可选）
        token: 访问令牌（可选）
    """
    if not MODELSCOPE_AVAILABLE:
        print("❌ 错误: 请安装modelscope库")
        print("安装命令: pip install modelscope")
        return False
    
    # 验证文件存在
    if not os.path.exists(file_path):
        print(f"❌ 错误: 文件不存在: {file_path}")
        return False
    
    # 验证仓库类型
    if repo_type not in REPOSITORIES:
        print(f"❌ 错误: 无效的仓库类型: {repo_type}")
        print(f"可用类型: {list(REPOSITORIES.keys())}")
        return False
    
    # 使用默认token
    token = token or DEFAULT_TOKEN
    repo_id = REPOSITORIES[repo_type]
    
    # 设置远程路径
    if not remote_path:
        remote_path = os.path.basename(file_path)
    
    try:
        # 初始化API
        api = HubApi()
        api.login(token)
        
        print(f"📤 开始上传文件到 {repo_id}")
        print(f"   本地文件: {file_path}")
        print(f"   远程路径: {remote_path}")
        
        # 上传文件
        api.upload_file(
            path_or_fileobj=file_path,
            path_in_repo=remote_path,
            repo_id=repo_id,
            repo_type='dataset',
            commit_message=f'Upload: {os.path.basename(file_path)}'
        )
        
        print(f"✅ 上传成功!")
        print(f"   访问地址: https://www.modelscope.cn/datasets/{repo_id}")
        return True
    
    except Exception as e:
        print(f"❌ 上传失败: {e}")
        return False

def upload_folder(folder_path: str, repo_type: str, remote_path: str = None, token: str = None):
    """
    上传文件夹到魔搭仓库
    
    Args:
        folder_path: 本地文件夹路径
        repo_type: 仓库类型 (input/output_mkv/output_webp)
        remote_path: 远程路径（可选）
        token: 访问令牌（可选）
    """
    if not MODELSCOPE_AVAILABLE:
        print("❌ 错误: 请安装modelscope库")
        return False
    
    # 验证文件夹存在
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        print(f"❌ 错误: 文件夹不存在: {folder_path}")
        return False
    
    # 验证仓库类型
    if repo_type not in REPOSITORIES:
        print(f"❌ 错误: 无效的仓库类型: {repo_type}")
        return False
    
    token = token or DEFAULT_TOKEN
    repo_id = REPOSITORIES[repo_type]
    
    # 设置远程路径
    if not remote_path:
        remote_path = os.path.basename(folder_path)
    
    try:
        # 初始化API
        api = HubApi()
        api.login(token)
        
        print(f"📤 开始上传文件夹到 {repo_id}")
        print(f"   本地文件夹: {folder_path}")
        print(f"   远程路径: {remote_path}")
        
        # 上传文件夹
        api.upload_folder(
            repo_id=repo_id,
            folder_path=folder_path,
            path_in_repo=remote_path,
            commit_message=f'Upload folder: {os.path.basename(folder_path)}',
            repo_type='dataset'
        )
        
        print(f"✅ 上传成功!")
        print(f"   访问地址: https://www.modelscope.cn/datasets/{repo_id}")
        return True
    
    except Exception as e:
        print(f"❌ 上传失败: {e}")
        return False

def list_repositories():
    """列出可用的仓库"""
    print("📋 可用的魔搭仓库:")
    for repo_type, repo_id in REPOSITORIES.items():
        print(f"   {repo_type:12} -> {repo_id}")
        print(f"                -> https://www.modelscope.cn/datasets/{repo_id}")
    print()

def main():
    parser = argparse.ArgumentParser(description="魔搭社区上传工具")
    parser.add_argument('action', choices=['file', 'folder', 'list'], 
                       help='操作类型: file(上传文件), folder(上传文件夹), list(列出仓库)')
    parser.add_argument('--path', '-p', required=False, 
                       help='本地文件或文件夹路径')
    parser.add_argument('--repo', '-r', choices=list(REPOSITORIES.keys()),
                       default='input', help='目标仓库类型')
    parser.add_argument('--remote', '-m', help='远程路径（可选）')
    parser.add_argument('--token', '-t', help='访问令牌（可选）')
    
    args = parser.parse_args()
    
    if args.action == 'list':
        list_repositories()
        return 0
    
    if not args.path:
        print("❌ 错误: 请指定文件或文件夹路径")
        return 1
    
    if args.action == 'file':
        success = upload_file(args.path, args.repo, args.remote, args.token)
    elif args.action == 'folder':
        success = upload_folder(args.path, args.repo, args.remote, args.token)
    
    return 0 if success else 1

if __name__ == "__main__":
    try:
        exit(main())
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
        exit(130)
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        exit(1)
