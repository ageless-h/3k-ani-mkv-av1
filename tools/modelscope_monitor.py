#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
魔搭仓库监控器
监控 https://www.modelscope.cn/datasets/ageless/3k-animation-mkv-av1 仓库
当检测到新的完整文件夹上传完成时，自动加入处理队列
"""

import os
import sys
import time
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Set
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from modelscope.hub.api import HubApi
    MODELSCOPE_AVAILABLE = True
except ImportError:
    MODELSCOPE_AVAILABLE = False

from config.config import Config
from src.utils import setup_logging

class ModelScopeMonitor:
    """魔搭仓库监控器"""
    
    def __init__(self, token: str = None, logger=None):
        self.token = token or Config.MODELSCOPE_TOKEN
        self.logger = logger or setup_logging()
        
        if not MODELSCOPE_AVAILABLE:
            raise ImportError("请安装modelscope: pip install modelscope")
        
        # 初始化API
        self.api = HubApi()
        try:
            self.api.login(self.token)
            self.logger.info("魔搭API登录成功")
        except Exception as e:
            self.logger.error(f"魔搭API登录失败: {e}")
            raise
        
        # 配置
        self.repo_id = "ageless/3k-animation-mkv-av1"
        self.monitor_interval = 300  # 5分钟检查一次
        self.min_folder_stable_time = 600  # 文件夹10分钟内无变化才认为上传完成
        
        # 状态文件
        self.state_file = "log/monitor_state.json"
        self.queue_file = "log/processing_queue.json"
        
        # 加载状态
        self.last_state = self.load_state()
        self.processing_queue = self.load_queue()
        
        # 确保日志目录存在
        os.makedirs("log", exist_ok=True)
    
    def load_state(self) -> Dict:
        """加载上次的仓库状态"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"加载状态文件失败: {e}")
        return {"folders": {}, "last_check": None}
    
    def save_state(self):
        """保存当前仓库状态"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.last_state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存状态文件失败: {e}")
    
    def load_queue(self) -> List[Dict]:
        """加载处理队列"""
        try:
            if os.path.exists(self.queue_file):
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"加载队列文件失败: {e}")
        return []
    
    def save_queue(self):
        """保存处理队列"""
        try:
            with open(self.queue_file, 'w', encoding='utf-8') as f:
                json.dump(self.processing_queue, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存队列文件失败: {e}")
    
    def get_repository_structure(self) -> Dict:
        """获取仓库的文件结构"""
        try:
            self.logger.info("正在获取仓库文件结构...")
            
            # 使用CLI获取文件列表（更可靠）
            import subprocess
            result = subprocess.run([
                "modelscope", "download", self.repo_id,
                "--cache_dir", "/tmp/monitor_cache",
                "--include", "**/*"
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                self.logger.error(f"获取仓库结构失败: {result.stderr}")
                return {}
            
            # 分析下载的文件结构
            cache_dir = "/tmp/monitor_cache"
            repo_structure = {"folders": {}, "files": []}
            
            if os.path.exists(cache_dir):
                for root, dirs, files in os.walk(cache_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, cache_dir)
                        
                        # 获取文件信息
                        try:
                            stat = os.stat(file_path)
                            file_info = {
                                "path": rel_path,
                                "size": stat.st_size,
                                "mtime": stat.st_mtime
                            }
                            repo_structure["files"].append(file_info)
                            
                            # 按文件夹分组
                            folder = os.path.dirname(rel_path)
                            if folder and folder != '.':
                                if folder not in repo_structure["folders"]:
                                    repo_structure["folders"][folder] = {
                                        "files": [],
                                        "total_size": 0,
                                        "last_modified": 0,
                                        "file_count": 0
                                    }
                                
                                repo_structure["folders"][folder]["files"].append(file_info)
                                repo_structure["folders"][folder]["total_size"] += stat.st_size
                                repo_structure["folders"][folder]["last_modified"] = max(
                                    repo_structure["folders"][folder]["last_modified"],
                                    stat.st_mtime
                                )
                                repo_structure["folders"][folder]["file_count"] += 1
                        
                        except OSError:
                            continue
            
            self.logger.info(f"发现 {len(repo_structure['folders'])} 个文件夹")
            return repo_structure
        
        except Exception as e:
            self.logger.error(f"获取仓库结构失败: {e}")
            return {}
    
    def calculate_folder_hash(self, folder_info: Dict) -> str:
        """计算文件夹的hash值（基于文件列表和大小）"""
        data = []
        for file_info in sorted(folder_info.get("files", []), key=lambda x: x["path"]):
            data.append(f"{file_info['path']}:{file_info['size']}")
        
        content = "|".join(data)
        return hashlib.md5(content.encode()).hexdigest()
    
    def detect_completed_folders(self, current_structure: Dict, force_all: bool = False) -> List[str]:
        """检测已完成上传的文件夹"""
        completed_folders = []
        current_time = time.time()
        
        for folder_name, folder_info in current_structure.get("folders", {}).items():
            # 跳过根目录文件
            if not folder_name or folder_name == '.':
                continue
            
            # 检查是否已经在队列中
            already_queued = any(item["folder"] == folder_name for item in self.processing_queue)
            if already_queued:
                continue
            
            # 如果强制模式（初始化扫描），直接添加所有有文件的文件夹
            if force_all:
                if folder_info["file_count"] > 0:
                    completed_folders.append(folder_name)
                    self.logger.info(f"初始化扫描发现文件夹: {folder_name} ({folder_info['file_count']} 文件)")
                continue
            
            # 正常监控模式：检查稳定性
            # 计算当前文件夹hash
            current_hash = self.calculate_folder_hash(folder_info)
            
            # 检查是否是新文件夹或有变化
            last_folder_info = self.last_state.get("folders", {}).get(folder_name, {})
            last_hash = last_folder_info.get("hash", "")
            last_check_time = last_folder_info.get("last_check_time", 0)
            
            # 如果文件夹内容有变化，更新检查时间
            if current_hash != last_hash:
                self.last_state.setdefault("folders", {})[folder_name] = {
                    "hash": current_hash,
                    "last_check_time": current_time,
                    "file_count": folder_info["file_count"],
                    "total_size": folder_info["total_size"],
                    "last_modified": folder_info["last_modified"]
                }
                self.logger.info(f"文件夹有更新: {folder_name} ({folder_info['file_count']} 文件)")
                continue
            
            # 如果文件夹内容稳定超过阈值时间，认为上传完成
            if current_time - last_check_time >= self.min_folder_stable_time:
                if folder_info["file_count"] > 0:
                    completed_folders.append(folder_name)
                    self.logger.info(f"检测到完成的文件夹: {folder_name}")
        
        return completed_folders
    
    def add_to_queue(self, folder_name: str, folder_info: Dict):
        """将文件夹添加到处理队列"""
        queue_item = {
            "folder": folder_name,
            "file_count": folder_info["file_count"],
            "total_size": folder_info["total_size"],
            "added_time": datetime.now().isoformat(),
            "status": "pending",
            "priority": self.calculate_priority(folder_info)
        }
        
        self.processing_queue.append(queue_item)
        
        # 按优先级排序（小文件夹优先）
        self.processing_queue.sort(key=lambda x: x["priority"])
        
        self.save_queue()
        self.logger.info(f"文件夹已加入处理队列: {folder_name} "
                        f"({folder_info['file_count']} 文件, {folder_info['total_size']/(1024**3):.2f} GB)")
    
    def calculate_priority(self, folder_info: Dict) -> int:
        """计算处理优先级（数值越小优先级越高）"""
        # 基于文件数量和大小计算优先级
        file_count = folder_info["file_count"]
        total_size_gb = folder_info["total_size"] / (1024**3)
        
        # 小文件夹优先
        if file_count <= 10 and total_size_gb <= 5:
            return 1  # 高优先级
        elif file_count <= 50 and total_size_gb <= 20:
            return 2  # 中优先级
        else:
            return 3  # 低优先级
    
    def get_pending_queue(self) -> List[Dict]:
        """获取待处理的队列项目"""
        return [item for item in self.processing_queue if item["status"] == "pending"]
    
    def mark_as_processing(self, folder_name: str):
        """标记文件夹为处理中"""
        for item in self.processing_queue:
            if item["folder"] == folder_name:
                item["status"] = "processing"
                item["start_time"] = datetime.now().isoformat()
                break
        self.save_queue()
    
    def mark_as_completed(self, folder_name: str, success: bool = True):
        """标记文件夹处理完成"""
        for item in self.processing_queue:
            if item["folder"] == folder_name:
                item["status"] = "completed" if success else "failed"
                item["end_time"] = datetime.now().isoformat()
                break
        self.save_queue()
    
    def monitor_once(self, force_all: bool = False) -> int:
        """执行一次监控检查"""
        try:
            if force_all:
                self.logger.info("开始初始化扫描，将所有现有文件夹加入队列...")
            else:
                self.logger.info("开始监控检查...")
            
            # 获取当前仓库结构
            current_structure = self.get_repository_structure()
            if not current_structure:
                self.logger.warning("无法获取仓库结构")
                return 0
            
            # 检测完成的文件夹
            completed_folders = self.detect_completed_folders(current_structure, force_all)
            
            # 添加到处理队列
            for folder_name in completed_folders:
                folder_info = current_structure["folders"][folder_name]
                self.add_to_queue(folder_name, folder_info)
            
            # 更新检查时间
            self.last_state["last_check"] = datetime.now().isoformat()
            self.save_state()
            
            # 显示队列状态
            pending_count = len(self.get_pending_queue())
            if pending_count > 0:
                self.logger.info(f"当前待处理队列: {pending_count} 个文件夹")
            
            return len(completed_folders)
        
        except Exception as e:
            self.logger.error(f"监控检查失败: {e}")
            return 0
    
    def initialize_queue_from_existing(self) -> int:
        """初始化队列：扫描现有数据并全部加入队列"""
        self.logger.info("正在执行初始化扫描，将现有所有文件夹加入处理队列...")
        return self.monitor_once(force_all=True)
    
    def run_monitor(self):
        """运行持续监控"""
        self.logger.info(f"开始监控魔搭仓库: {self.repo_id}")
        self.logger.info(f"监控间隔: {self.monitor_interval} 秒")
        self.logger.info(f"稳定时间阈值: {self.min_folder_stable_time} 秒")
        
        try:
            while True:
                new_folders = self.monitor_once()
                
                if new_folders > 0:
                    self.logger.info(f"本次检查发现 {new_folders} 个新完成的文件夹")
                
                # 等待下次检查
                self.logger.debug(f"等待 {self.monitor_interval} 秒后进行下次检查...")
                time.sleep(self.monitor_interval)
        
        except KeyboardInterrupt:
            self.logger.info("监控已停止")
        except Exception as e:
            self.logger.error(f"监控运行失败: {e}")
            raise

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="魔搭仓库监控器")
    parser.add_argument('--once', action='store_true', help='只执行一次检查')
    parser.add_argument('--queue', action='store_true', help='显示当前队列状态')
    parser.add_argument('--interval', type=int, default=300, help='监控间隔(秒)')
    parser.add_argument('--init', action='store_true', help='初始化模式：扫描现有数据并全部加入队列')
    parser.add_argument('--auto', action='store_true', help='自动模式：先初始化再持续监控')
    
    args = parser.parse_args()
    
    try:
        monitor = ModelScopeMonitor()
        monitor.monitor_interval = args.interval
        
        if args.queue:
            # 显示队列状态
            pending = monitor.get_pending_queue()
            print(f"📋 当前待处理队列: {len(pending)} 个文件夹")
            for item in pending:
                print(f"  📁 {item['folder']} - {item['file_count']} 文件 "
                     f"({item['total_size']/(1024**3):.2f} GB) "
                     f"[优先级: {item['priority']}]")
        
        elif args.init:
            # 初始化模式：扫描现有数据
            new_folders = monitor.initialize_queue_from_existing()
            print(f"✅ 初始化完成，将 {new_folders} 个现有文件夹加入队列")
        
        elif args.once:
            # 只执行一次检查
            new_folders = monitor.monitor_once()
            print(f"✅ 检查完成，发现 {new_folders} 个新完成的文件夹")
        
        elif args.auto:
            # 自动模式：先初始化再监控
            print("🚀 自动模式启动")
            
            # 步骤1：初始化扫描
            new_folders = monitor.initialize_queue_from_existing()
            print(f"✅ 初始化完成，将 {new_folders} 个现有文件夹加入队列")
            
            # 步骤2：持续监控
            print("📡 开始持续监控新上传的文件...")
            monitor.run_monitor()
        
        else:
            # 持续监控
            monitor.run_monitor()
    
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
        return 130
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 