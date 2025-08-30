#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动配置动画系列文件夹列表
当自动扫描失败时使用
"""

import os
import sys

def manual_setup():
    """手动设置动画系列文件夹"""
    print("🎬 动画系列文件夹手动配置工具")
    print("=" * 50)
    
    print("\n📝 请手动输入您仓库中的动画系列文件夹名称")
    print("（例如：暗芝居 第1季、某某动画 第1季等）")
    print("每行输入一个文件夹名称，空行结束输入\n")
    
    folders = []
    folder_num = 1
    
    while True:
        prompt = f"动画系列 {folder_num}: "
        folder_name = input(prompt).strip()
        
        if not folder_name:
            break
            
        folders.append(folder_name)
        folder_num += 1
        print(f"✅ 已添加: {folder_name}")
    
    if not folders:
        print("❌ 没有添加任何文件夹")
        return False
    
    print(f"\n📊 总共添加了 {len(folders)} 个动画系列:")
    for i, folder in enumerate(folders, 1):
        print(f"  {i}. {folder}")
    
    # 生成配置代码
    config_lines = []
    config_lines.append("    # 手动配置的动画系列文件夹")
    config_lines.append("    MANUAL_FOLDER_LIST = [")
    
    for folder in folders:
        # 根据文件夹名称估算优先级
        priority = 1 if len(folders) <= 5 else 2  # 少量文件夹高优先级
        config_lines.append(f'        {{"name": "{folder}", "priority": {priority}}},')
    
    config_lines.append("    ]")
    config_lines.append("")
    config_lines.append("    # 启用手动文件夹列表")
    config_lines.append("    USE_MANUAL_FOLDER_LIST = True")
    
    config_text = "\n".join(config_lines)
    
    print(f"\n📝 生成的配置代码:")
    print("-" * 40)
    print(config_text)
    print("-" * 40)
    
    # 询问是否自动更新配置文件
    choice = input(f"\n❓ 是否自动更新 config/config.py 文件？(y/n): ").lower().strip()
    
    if choice == 'y':
        try:
            update_config_file(config_text)
            print("✅ 配置文件已更新！")
            return True
        except Exception as e:
            print(f"❌ 更新配置文件失败: {e}")
            print("请手动复制上面的配置代码到 config/config.py")
            return False
    else:
        print("📋 请手动复制上面的配置代码到 config/config.py 文件中")
        print("替换现有的 MANUAL_FOLDER_LIST 和 USE_MANUAL_FOLDER_LIST")
        return False

def update_config_file(new_config):
    """更新配置文件"""
    config_file = "config/config.py"
    
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"配置文件不存在: {config_file}")
    
    # 读取现有配置
    with open(config_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 查找并替换配置段
    new_lines = []
    skip_lines = False
    manual_config_added = False
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # 检查是否是手动配置的开始
        if "MANUAL_FOLDER_LIST" in line or "USE_MANUAL_FOLDER_LIST" in line:
            if not manual_config_added:
                # 添加新配置
                new_lines.append(new_config + "\n")
                manual_config_added = True
            
            # 跳过旧的手动配置行
            if "MANUAL_FOLDER_LIST" in line:
                # 跳过整个列表
                while i < len(lines) and not lines[i].strip().endswith(']'):
                    i += 1
                if i < len(lines):
                    i += 1  # 跳过结束的 ]
            elif "USE_MANUAL_FOLDER_LIST" in line:
                i += 1  # 跳过这一行
            continue
        
        new_lines.append(line)
        i += 1
    
    # 如果没有找到原有配置，在文件末尾添加
    if not manual_config_added:
        new_lines.append("\n" + new_config + "\n")
    
    # 写回文件
    with open(config_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

def test_config():
    """测试配置是否正确"""
    print("\n🧪 测试配置...")
    
    try:
        # 重新加载配置
        sys.path.insert(0, '.')
        if 'config.config' in sys.modules:
            del sys.modules['config.config']
        
        from config.config import Config
        
        if hasattr(Config, 'MANUAL_FOLDER_LIST') and hasattr(Config, 'USE_MANUAL_FOLDER_LIST'):
            if Config.USE_MANUAL_FOLDER_LIST and Config.MANUAL_FOLDER_LIST:
                print(f"✅ 配置正确！发现 {len(Config.MANUAL_FOLDER_LIST)} 个动画系列")
                for i, folder_config in enumerate(Config.MANUAL_FOLDER_LIST, 1):
                    name = folder_config.get('name', '未知')
                    priority = folder_config.get('priority', 2)
                    print(f"  {i}. {name} (优先级: {priority})")
                return True
            else:
                print("❌ 手动配置未启用或列表为空")
                return False
        else:
            print("❌ 配置文件中缺少必要的配置项")
            return False
    
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        return False

def main():
    print("🎯 这个工具将帮助您手动配置动画系列文件夹列表")
    print("适用于自动扫描失败的情况\n")
    
    success = manual_setup()
    
    if success:
        # 测试配置
        if test_config():
            print("\n🎉 配置完成！现在可以运行监控器了:")
            print("   python3 debug_monitor.py")
            print("   或")
            print("   bash start_auto_processing.sh")
    
    print("\n📖 提示：")
    print("- 文件夹名称需要与魔搭仓库中的实际文件夹名称完全一致")
    print("- 可以随时重新运行此工具来更新配置")
    print("- 配置完成后，监控器将使用这些文件夹开始处理")

if __name__ == "__main__":
    main() 