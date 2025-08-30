#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控器调试脚本
用于诊断为什么监控器没有找到任何数据
"""

import os
import sys
import json
import subprocess
from pathlib import Path

# 添加项目路径
sys.path.append('.')

def test_modelscope_cli():
    """测试ModelScope CLI"""
    print("🔍 测试 ModelScope CLI...")
    
    try:
        # 测试modelscope命令是否可用
        result = subprocess.run(["modelscope", "--version"], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"✅ ModelScope CLI版本: {result.stdout.strip()}")
        else:
            print(f"❌ ModelScope CLI错误: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ ModelScope CLI不可用: {e}")
        return False
    
    return True

def test_modelscope_login():
    """测试ModelScope登录状态"""
    print("\n🔐 测试 ModelScope 登录状态...")
    
    try:
        from modelscope.hub.api import HubApi
        from config.config import Config
        
        api = HubApi()
        api.login(Config.MODELSCOPE_TOKEN)
        print("✅ ModelScope API登录成功")
        return True
    except Exception as e:
        print(f"❌ ModelScope API登录失败: {e}")
        return False

def test_repository_access():
    """测试仓库访问"""
    print("\n📦 测试仓库访问...")
    
    repo_id = "ageless/3k-animation-mkv-av1"
    
    try:
        # 尝试列出仓库内容
        result = subprocess.run([
            "modelscope", "ls", repo_id, "--recursive"
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            print(f"✅ 仓库访问成功，发现 {len(lines)} 个条目")
            
            # 显示前10个条目
            print("📁 仓库内容样例:")
            for i, line in enumerate(lines[:10]):
                print(f"  {i+1}. {line}")
            if len(lines) > 10:
                print(f"  ... 还有 {len(lines) - 10} 个条目")
            
            return True
        else:
            print(f"❌ 仓库访问失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 仓库访问异常: {e}")
        return False

def test_download_structure():
    """测试下载结构"""
    print("\n⬇️  测试下载仓库结构...")
    
    repo_id = "ageless/3k-animation-mkv-av1"
    cache_dir = "/tmp/debug_monitor_cache"
    
    try:
        # 清理旧缓存
        if os.path.exists(cache_dir):
            import shutil
            shutil.rmtree(cache_dir)
        
        # 下载文件结构
        result = subprocess.run([
            "modelscope", "download", repo_id,
            "--cache_dir", cache_dir,
            "--include", "**/*"
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            print("✅ 下载成功")
            
            # 分析下载的结构
            folder_count = 0
            file_count = 0
            
            if os.path.exists(cache_dir):
                for root, dirs, files in os.walk(cache_dir):
                    folder_count += len(dirs)
                    for file in files:
                        file_count += 1
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, cache_dir)
                        if file_count <= 5:  # 只显示前5个文件
                            file_size = os.path.getsize(file_path)
                            print(f"  📄 {rel_path} ({file_size} bytes)")
            
            print(f"📊 总计: {folder_count} 个文件夹, {file_count} 个文件")
            return True
        else:
            print(f"❌ 下载失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 下载异常: {e}")
        return False

def test_monitor_logic():
    """测试监控器逻辑"""
    print("\n🔍 测试监控器逻辑...")
    
    try:
        from tools.modelscope_monitor import ModelScopeMonitor
        
        monitor = ModelScopeMonitor()
        
        # 测试获取仓库结构
        structure = monitor.get_repository_structure()
        
        if structure:
            folder_count = len(structure.get("folders", {}))
            file_count = len(structure.get("files", []))
            print(f"✅ 监控器解析成功: {folder_count} 个文件夹, {file_count} 个文件")
            
            # 显示文件夹信息
            for folder_name, folder_info in list(structure.get("folders", {}).items())[:3]:
                print(f"  📁 {folder_name}: {folder_info['file_count']} 文件, {folder_info['total_size']/(1024**2):.1f} MB")
            
            return True
        else:
            print("❌ 监控器无法获取仓库结构")
            return False
    except Exception as e:
        print(f"❌ 监控器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_queue_initialization():
    """测试队列初始化"""
    print("\n📋 测试队列初始化...")
    
    try:
        from tools.modelscope_monitor import ModelScopeMonitor
        
        monitor = ModelScopeMonitor()
        
        # 执行初始化
        new_folders = monitor.initialize_queue_from_existing()
        print(f"✅ 初始化完成，添加了 {new_folders} 个文件夹到队列")
        
        # 检查队列内容
        pending = monitor.get_pending_queue()
        print(f"📊 当前队列: {len(pending)} 个待处理项目")
        
        for item in pending[:3]:  # 显示前3个
            print(f"  📁 {item['folder']}: {item['file_count']} 文件, 优先级 {item['priority']}")
        
        return len(pending) > 0
    except Exception as e:
        print(f"❌ 队列初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("🚀 监控器调试工具")
    print("=" * 50)
    
    tests = [
        ("ModelScope CLI", test_modelscope_cli),
        ("ModelScope 登录", test_modelscope_login),
        ("仓库访问", test_repository_access),
        ("下载结构", test_download_structure),
        ("监控器逻辑", test_monitor_logic),
        ("队列初始化", test_queue_initialization),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} - 通过")
            else:
                failed += 1
                print(f"❌ {test_name} - 失败")
        except Exception as e:
            failed += 1
            print(f"💥 {test_name} - 异常: {e}")
    
    print(f"\n{'='*50}")
    print(f"🏁 测试结果: {passed} 通过, {failed} 失败")
    
    if failed > 0:
        print("\n💡 建议:")
        print("1. 检查网络连接")
        print("2. 确认ModelScope token有效")
        print("3. 检查仓库权限")
        print("4. 查看详细错误日志")

if __name__ == "__main__":
    main() 