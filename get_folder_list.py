#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速获取仓库文件夹列表的工具
帮助配置手动文件夹列表
"""

import subprocess
import sys
import os
from pathlib import Path

def get_folder_list_simple():
    """使用简单的方法获取文件夹列表"""
    print("🔍 尝试获取仓库文件夹列表...")
    
    repo_id = "ageless/3k-animation-mkv-av1"
    cache_dir = "/tmp/quick_folder_check"
    
    try:
        # 清理缓存
        if os.path.exists(cache_dir):
            import shutil
            shutil.rmtree(cache_dir)
        
        print("📥 尝试快速下载...")
        
        # 只尝试下载README等小文件
        result = subprocess.run([
            "modelscope", "download", 
            "--dataset", repo_id,
            "--cache_dir", cache_dir,
            "--include", "README*"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print("⚠️  README下载失败，尝试基础下载（可能较慢）...")
            
            # 尝试基础下载但设置较短的超时
            result = subprocess.run([
                "modelscope", "download", 
                "--dataset", repo_id,
                "--cache_dir", cache_dir
            ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ 下载成功！分析文件夹结构...")
            
            folders = set()
            if os.path.exists(cache_dir):
                for root, dirs, files in os.walk(cache_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, cache_dir)
                        
                        if rel_path.startswith('.') or 'git' in rel_path.lower():
                            continue
                        
                        folder = os.path.dirname(rel_path)
                        if folder and folder != '.':
                            # 获取顶级文件夹
                            folder_parts = folder.split(os.sep)
                            main_folder = folder_parts[0]
                            folders.add(main_folder)
            
            if folders:
                print(f"\n📁 发现 {len(folders)} 个文件夹:")
                for i, folder in enumerate(sorted(folders), 1):
                    print(f"  {i}. {folder}")
                
                print(f"\n📝 配置示例（添加到 config/config.py 中的 MANUAL_FOLDER_LIST）:")
                print("MANUAL_FOLDER_LIST = [")
                for folder in sorted(folders):
                    print(f'    {{"name": "{folder}", "priority": 2}},')
                print("]")
                
                return list(folders)
            else:
                print("❌ 未发现任何文件夹")
                return []
        else:
            print(f"❌ 下载失败: {result.stderr}")
            return []
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        return []

def manual_config_helper():
    """手动配置助手"""
    print("\n" + "="*50)
    print("📝 手动配置助手")
    print("="*50)
    
    print("\n如果自动获取失败，您可以：")
    print("1. 手动浏览仓库页面：https://www.modelscope.cn/datasets/ageless/3k-animation-mkv-av1")
    print("2. 记录文件夹名称")
    print("3. 在下面输入文件夹名称（每行一个，空行结束）:")
    
    folders = []
    while True:
        folder = input("文件夹名称: ").strip()
        if not folder:
            break
        folders.append(folder)
    
    if folders:
        print(f"\n📝 生成的配置（添加到 config/config.py）:")
        print("MANUAL_FOLDER_LIST = [")
        for folder in folders:
            print(f'    {{"name": "{folder}", "priority": 2}},')
        print("]")
        
        # 保存到文件
        config_text = "MANUAL_FOLDER_LIST = [\n"
        for folder in folders:
            config_text += f'    {{"name": "{folder}", "priority": 2}},\n'
        config_text += "]\n"
        
        with open("manual_folder_config.txt", "w", encoding="utf-8") as f:
            f.write(config_text)
        
        print(f"\n💾 配置已保存到: manual_folder_config.txt")
        print("请将内容复制到 config/config.py 中的 MANUAL_FOLDER_LIST")

def main():
    print("🚀 魔搭仓库文件夹列表获取工具")
    print("="*50)
    
    # 尝试自动获取
    folders = get_folder_list_simple()
    
    if not folders:
        # 如果自动获取失败，提供手动配置选项
        choice = input("\n自动获取失败，是否使用手动配置助手？(y/n): ").lower()
        if choice == 'y':
            manual_config_helper()
    
    print("\n🎉 完成！")

if __name__ == "__main__":
    main() 