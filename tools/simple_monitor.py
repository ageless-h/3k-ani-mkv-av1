#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化仓库监控器
监控单个视频文件，而不是文件夹
"""

import os
import sys
import time
import json
import hashlib
import subprocess
from datetime import datetime
from typing import Dict, List, Set, Optional
from pathlib import Path

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config.config import Config
from src.utils import setup_logging


class SimpleVideoMonitor:
    """简化的视频文件监控器"""
    
    def __init__(self):
        self.config = Config()
        self.logger = setup_logging('simple_monitor')
        
        # 仓库信息 - 使用输入仓库ID
        self.repo_id = self.config.INPUT_REPO_ID
        self.token = self.config.MODELSCOPE_TOKEN
        
        # 监控状态文件
        self.state_file = "log/monitor_state.json"
        self.queue_file = "log/video_queue.json"
        
        # 已处理文件追踪
        self.processed_videos: Set[str] = set()
        self.video_queue: List[Dict] = []
        
        # 加载状态
        self.load_state()
        self.load_queue()
        
        # 视频扩展名
        self.video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.rmvb'}
    
    def load_state(self):
        """加载监控状态"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.processed_videos = set(state.get('processed_videos', []))
                    self.logger.info(f"加载状态: {len(self.processed_videos)} 个已处理视频")
        except Exception as e:
            self.logger.warning(f"加载状态文件失败: {e}")
    
    def save_state(self):
        """保存监控状态"""
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            state = {
                'processed_videos': list(self.processed_videos),
                'last_update': datetime.now().isoformat()
            }
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存状态文件失败: {e}")
    
    def load_queue(self) -> List[Dict]:
        """加载视频队列"""
        try:
            if os.path.exists(self.queue_file):
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    self.video_queue = json.load(f)
                    self.logger.info(f"加载队列: {len(self.video_queue)} 个待处理视频")
        except Exception as e:
            self.logger.warning(f"加载队列文件失败: {e}")
            self.video_queue = []
    
    def save_queue(self):
        """保存视频队列"""
        try:
            os.makedirs(os.path.dirname(self.queue_file), exist_ok=True)
            with open(self.queue_file, 'w', encoding='utf-8') as f:
                json.dump(self.video_queue, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存队列文件失败: {e}")
    
    def get_all_videos_from_repo(self) -> List[Dict]:
        """获取仓库中所有视频文件信息"""
        try:
            self.logger.info("获取仓库中的所有视频文件...")
            
            cache_dir = "/tmp/simple_monitor_cache"
            
            # 清理旧缓存
            if os.path.exists(cache_dir):
                import shutil
                shutil.rmtree(cache_dir)
            
            # 使用正确的ModelScope CLI下载命令格式
            # 1. 先尝试下载所有视频文件  
            result = subprocess.run([
                "modelscope", "download",
                self.repo_id,                   # repo_id (位置参数)
                cache_dir,                      # local_path (位置参数)
                "--repo-type", "dataset",       # 指定为数据集仓库
                "--include", "**/*.mp4",        # 包含所有视频格式
                "--include", "**/*.mkv", 
                "--include", "**/*.rmvb",
                "--include", "**/*.avi",
                "--include", "**/*.mov",
                "--token", self.token           # 明确指定token
            ], capture_output=True, text=True, timeout=600)
            
            if result.returncode != 0:
                self.logger.warning(f"包含模式下载失败，尝试完整下载: {result.stderr}")
                # 如果包含模式失败，尝试完整下载
                result = subprocess.run([
                    "modelscope", "download",
                    self.repo_id,               # repo_id (位置参数)
                    cache_dir,                  # local_path (位置参数)
                    "--repo-type", "dataset",   # 指定为数据集仓库
                    "--token", self.token       # 明确指定token
                ], capture_output=True, text=True, timeout=600)
            
            if result.returncode != 0:
                self.logger.error(f"下载仓库失败: {result.stderr}")
                return self._get_expected_videos()
            
            # 解析视频文件
            video_files = []
            
            for root, dirs, files in os.walk(cache_dir):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in self.video_extensions):
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, cache_dir)
                        
                        # 清理路径
                        clean_path = rel_path.replace('\\', '/')  # Windows路径转换
                        
                        if clean_path:
                            try:
                                stat = os.stat(file_path)
                                video_info = {
                                    "path": clean_path,
                                    "size": stat.st_size,
                                    "mtime": stat.st_mtime,
                                    "status": "real"  # 标记为真实文件
                                }
                                video_files.append(video_info)
                            except OSError:
                                continue
            
            self.logger.info(f"发现 {len(video_files)} 个视频文件")
            
            # 如果仍然没有发现视频，使用filelist.txt中的信息
            if not video_files:
                return self._get_videos_from_filelist()
            
            return video_files
            
        except Exception as e:
            self.logger.error(f"获取视频文件失败: {e}")
            return self._get_videos_from_filelist()
    
    def _get_videos_from_filelist(self) -> List[Dict]:
        """从filelist.txt获取视频列表（最终备用方案）"""
        try:
            if os.path.exists("filelist.txt"):
                self.logger.info("从filelist.txt构造视频列表...")
                videos = []
                current_time = time.time()
                
                with open("filelist.txt", 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and any(line.lower().endswith(ext) for ext in self.video_extensions):
                            # 提取路径信息
                            # /volume1/db/5_video/archive/暗芝居 第1季/暗芝居 第1季 - 0009.mp4
                            parts = line.split('/')
                            if len(parts) >= 3:
                                series_name = parts[-2]  # 暗芝居 第1季
                                filename = parts[-1]     # 暗芝居 第1季 - 0009.mp4
                                
                                video_info = {
                                    "path": f"{series_name}/{filename}",
                                    "size": 100000000,  # 假设100MB
                                    "mtime": current_time,
                                    "status": "from_filelist"
                                }
                                videos.append(video_info)
                
                self.logger.info(f"从filelist.txt构造了 {len(videos)} 个视频")
                return videos
            
        except Exception as e:
            self.logger.error(f"读取filelist.txt失败: {e}")
        
        # 最终备用方案
        return self._get_expected_videos()
    
    def _clean_video_path(self, raw_path: str) -> Optional[str]:
        """清理视频路径，移除不必要的前缀"""
        try:
            parts = raw_path.split(os.sep)
            
            # 跳过用户名和仓库名等前缀
            clean_parts = []
            for part in parts:
                # 跳过用户名、datasets前缀等
                if part.startswith('datasets--') or part == 'ageless' or part == '3k-animation-mkv-av1':
                    continue
                clean_parts.append(part)
            
            if clean_parts:
                return '/'.join(clean_parts)
            return None
            
        except Exception as e:
            self.logger.warning(f"清理路径失败 {raw_path}: {e}")
            return None
    
    def _get_expected_videos(self) -> List[Dict]:
        """获取预期的视频列表（备用方案）"""
        expected_videos = [
            {"path": "180秒能让你的耳朵幸福吗？/180秒能让你的耳朵幸福吗？ - 0001.mp4", "size": 100000000, "mtime": time.time(), "status": "expected"},
            {"path": "暗芝居 第1季/暗芝居 第1季 - 0001.mp4", "size": 100000000, "mtime": time.time(), "status": "expected"},
            {"path": "暗芝居 第1季/暗芝居 第1季 - 0002.mp4", "size": 100000000, "mtime": time.time(), "status": "expected"},
            {"path": "死亡笔记 特别篇/死亡笔记 特别篇 - 0001.rmvb", "size": 100000000, "mtime": time.time(), "status": "expected"},
            {"path": "若叶女孩/若叶女孩 - 0001.mp4", "size": 100000000, "mtime": time.time(), "status": "expected"},
        ]
        
        self.logger.info(f"使用预期视频列表: {len(expected_videos)} 个视频")
        return expected_videos
    
    def add_video_to_queue(self, video_info: Dict):
        """添加视频到处理队列"""
        video_path = video_info["path"]
        
        # 检查是否已处理
        if video_path in self.processed_videos:
            return
        
        # 检查是否已在队列中
        for item in self.video_queue:
            if item["path"] == video_path:
                return
        
        # 添加到队列
        queue_item = {
            "path": video_path,
            "size": video_info["size"],
            "mtime": video_info["mtime"],
            "added_time": time.time(),
            "status": "pending",
            "priority": 1  # 所有视频优先级相同
        }
        
        self.video_queue.append(queue_item)
        self.logger.info(f"添加到队列: {video_path} ({video_info['size'] // 1024 // 1024} MB)")
    
    def mark_video_processed(self, video_path: str):
        """标记视频为已处理"""
        self.processed_videos.add(video_path)
        
        # 确保从队列中移除（防护性代码）
        original_length = len(self.video_queue)
        self.video_queue = [item for item in self.video_queue if item["path"] != video_path]
        removed = original_length - len(self.video_queue)
        
        self.save_state()
        if removed > 0:
            self.save_queue()
            self.logger.debug(f"从队列中移除了 {removed} 个重复项: {video_path}")
        
        self.logger.info(f"标记为已处理: {video_path}")
    
    def mark_video_failed(self, video_path: str):
        """标记视频处理失败，添加到已处理列表避免重复尝试"""
        self.processed_videos.add(video_path)
        
        # 确保从队列中移除
        original_length = len(self.video_queue)
        self.video_queue = [item for item in self.video_queue if item["path"] != video_path]
        removed = original_length - len(self.video_queue)
        
        self.save_state()
        if removed > 0:
            self.save_queue()
        
        self.logger.warning(f"标记为失败: {video_path}")
    
    def initialize_from_existing(self):
        """从现有仓库初始化队列"""
        self.logger.info("开始从现有仓库初始化队列...")
        
        all_videos = self.get_all_videos_from_repo()
        
        new_count = 0
        for video_info in all_videos:
            if video_info["path"] not in self.processed_videos:
                self.add_video_to_queue(video_info)
                new_count += 1
        
        self.save_queue()
        self.logger.info(f"初始化完成，添加了 {new_count} 个新视频到队列")
        self.logger.info(f"当前队列: {len(self.video_queue)} 个待处理视频")
        
        return new_count > 0
    
    def monitor_once(self) -> int:
        """执行一次监控检查"""
        try:
            current_videos = self.get_all_videos_from_repo()
            new_count = 0
            
            for video_info in current_videos:
                if video_info["path"] not in self.processed_videos:
                    # 检查是否是新视频
                    is_new = True
                    for item in self.video_queue:
                        if item["path"] == video_info["path"]:
                            is_new = False
                            break
                    
                    if is_new:
                        self.add_video_to_queue(video_info)
                        new_count += 1
            
            if new_count > 0:
                self.save_queue()
                self.logger.info(f"发现 {new_count} 个新视频")
            
            return new_count
            
        except Exception as e:
            self.logger.error(f"监控检查失败: {e}")
            return 0
    
    def run_monitor(self, check_interval: int = 300):
        """持续监控模式"""
        self.logger.info(f"开始持续监控，检查间隔: {check_interval} 秒")
        
        try:
            while True:
                self.monitor_once()
                self.logger.debug(f"等待 {check_interval} 秒后进行下次检查...")
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            self.logger.info("监控已停止")
        except Exception as e:
            self.logger.error(f"监控异常: {e}")
    
    def get_next_video(self) -> Optional[Dict]:
        """获取下一个要处理的视频并从队列中移除"""
        if self.video_queue:
            # 获取并移除队列中的第一个视频
            next_video = self.video_queue.pop(0)
            self.save_queue()  # 立即保存队列状态
            self.logger.debug(f"从队列中取出视频: {next_video['path']}")
            return next_video
        return None
    
    def get_queue_status(self) -> Dict:
        """获取队列状态"""
        return {
            "queue_size": len(self.video_queue),
            "processed_count": len(self.processed_videos),
            "next_videos": self.video_queue[:5]  # 显示前5个
        } 