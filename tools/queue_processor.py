#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
队列处理器
从监控器的队列中获取待处理文件夹，自动启动处理任务
"""

import os
import sys
import time
import json
from datetime import datetime
from typing import List, Dict

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main import AnimationProcessor
from src.utils import setup_logging, check_free_space
from config.config import Config

class QueueProcessor:
    """队列处理器"""
    
    def __init__(self, logger=None):
        self.logger = logger or setup_logging()
        self.config = Config()
        
        # 队列文件
        self.queue_file = "log/processing_queue.json"
        
        # 处理配置
        self.check_interval = 60  # 1分钟检查一次队列
        self.max_concurrent = 1   # 最大并发处理数
        
    def load_queue(self) -> List[Dict]:
        """加载处理队列"""
        try:
            if os.path.exists(self.queue_file):
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"加载队列文件失败: {e}")
        return []
    
    def save_queue(self, queue: List[Dict]):
        """保存处理队列"""
        try:
            with open(self.queue_file, 'w', encoding='utf-8') as f:
                json.dump(queue, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存队列文件失败: {e}")
    
    def get_pending_items(self) -> List[Dict]:
        """获取待处理的项目"""
        queue = self.load_queue()
        return [item for item in queue if item.get("status") == "pending"]
    
    def mark_item_status(self, folder_name: str, status: str):
        """更新项目状态"""
        queue = self.load_queue()
        for item in queue:
            if item["folder"] == folder_name:
                item["status"] = status
                if status == "processing":
                    item["start_time"] = datetime.now().isoformat()
                elif status in ["completed", "failed"]:
                    item["end_time"] = datetime.now().isoformat()
                break
        self.save_queue(queue)
    
    def process_folder(self, folder_info: Dict) -> bool:
        """处理单个文件夹"""
        folder_name = folder_info["folder"]
        
        try:
            self.logger.info(f"开始处理文件夹: {folder_name}")
            
            # 标记为处理中
            self.mark_item_status(folder_name, "processing")
            
            # 检查磁盘空间
            if not check_free_space(self.config.TEMP_DIR, self.config.MIN_FREE_SPACE_GB):
                self.logger.error("磁盘空间不足，跳过处理")
                self.mark_item_status(folder_name, "failed")
                return False
            
            # 初始化处理器
            processor = AnimationProcessor()
            
            # 获取文件夹中的视频文件
            video_files = self.get_folder_videos(folder_name)
            if not video_files:
                self.logger.warning(f"文件夹中没有找到视频文件: {folder_name}")
                self.mark_item_status(folder_name, "failed")
                return False
            
            # 按系列组织视频
            series_dict = processor.organize_videos_by_series(video_files)
            
            # 处理每个系列
            total_success = 0
            total_batches = 0
            
            for series_name, series_videos in series_dict.items():
                self.logger.info(f"处理系列: {series_name} ({len(series_videos)} 个视频)")
                
                # 分批处理
                batch_size = self.config.MAX_EPISODES_PER_BATCH
                for i in range(0, len(series_videos), batch_size):
                    batch_videos = series_videos[i:i + batch_size]
                    batch_name = f"{folder_name}_{series_name}_part{(i//batch_size)+1:02d}"
                    
                    # 处理批次
                    success = processor.process_videos_in_batch(batch_videos, batch_name)
                    total_batches += 1
                    
                    if success:
                        total_success += 1
                        self.logger.info(f"批次处理成功: {batch_name}")
                    else:
                        self.logger.error(f"批次处理失败: {batch_name}")
            
            # 判断整体成功率
            success_rate = (total_success / total_batches * 100) if total_batches > 0 else 0
            
            if success_rate >= 80:  # 80%以上成功率认为处理成功
                self.mark_item_status(folder_name, "completed")
                self.logger.info(f"文件夹处理完成: {folder_name} (成功率: {success_rate:.1f}%)")
                return True
            else:
                self.mark_item_status(folder_name, "failed")
                self.logger.error(f"文件夹处理失败: {folder_name} (成功率: {success_rate:.1f}%)")
                return False
        
        except Exception as e:
            self.logger.error(f"处理文件夹失败 {folder_name}: {e}")
            self.mark_item_status(folder_name, "failed")
            return False
    
    def get_folder_videos(self, folder_name: str) -> List[str]:
        """获取文件夹中的视频文件列表"""
        try:
            # 从魔搭管理器获取视频列表
            from src.modelscope_manager import ModelScopeManager
            
            manager = ModelScopeManager(self.config.MODELSCOPE_TOKEN, self.logger)
            all_videos = manager.get_available_videos()
            
            # 过滤属于指定文件夹的视频
            folder_videos = []
            for video_path in all_videos:
                # 检查视频是否属于这个文件夹
                if folder_name in video_path:
                    folder_videos.append(video_path)
            
            self.logger.info(f"文件夹 {folder_name} 包含 {len(folder_videos)} 个视频文件")
            return folder_videos
        
        except Exception as e:
            self.logger.error(f"获取文件夹视频列表失败 {folder_name}: {e}")
            return []
    
    def run_processor(self):
        """运行队列处理器"""
        self.logger.info("队列处理器启动")
        self.logger.info(f"检查间隔: {self.check_interval} 秒")
        self.logger.info(f"最大并发: {self.max_concurrent}")
        
        try:
            while True:
                # 获取待处理项目
                pending_items = self.get_pending_items()
                
                if not pending_items:
                    self.logger.debug("队列为空，等待新任务...")
                    time.sleep(self.check_interval)
                    continue
                
                # 检查当前处理中的任务数
                queue = self.load_queue()
                processing_count = len([item for item in queue if item.get("status") == "processing"])
                
                if processing_count >= self.max_concurrent:
                    self.logger.debug(f"已达到最大并发数 ({processing_count})，等待...")
                    time.sleep(self.check_interval)
                    continue
                
                # 处理队列中的第一个项目
                item_to_process = pending_items[0]
                self.logger.info(f"从队列中获取任务: {item_to_process['folder']}")
                
                # 检查磁盘空间
                if not check_free_space(self.config.TEMP_DIR, self.config.MIN_FREE_SPACE_GB):
                    self.logger.warning("磁盘空间不足，等待空间释放...")
                    time.sleep(300)  # 等待5分钟
                    continue
                
                # 处理项目
                success = self.process_folder(item_to_process)
                
                if success:
                    self.logger.info(f"✅ 任务完成: {item_to_process['folder']}")
                else:
                    self.logger.error(f"❌ 任务失败: {item_to_process['folder']}")
                
                # 短暂休息
                time.sleep(5)
        
        except KeyboardInterrupt:
            self.logger.info("队列处理器已停止")
        except Exception as e:
            self.logger.error(f"队列处理器运行失败: {e}")
            raise

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="队列处理器")
    parser.add_argument('--interval', type=int, default=60, help='检查间隔(秒)')
    parser.add_argument('--concurrent', type=int, default=1, help='最大并发数')
    parser.add_argument('--status', action='store_true', help='显示队列状态')
    
    args = parser.parse_args()
    
    try:
        processor = QueueProcessor()
        processor.check_interval = args.interval
        processor.max_concurrent = args.concurrent
        
        if args.status:
            # 显示队列状态
            queue = processor.load_queue()
            
            print("📊 队列状态统计:")
            print(f"  总任务: {len(queue)}")
            
            status_counts = {}
            for item in queue:
                status = item.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
            
            for status, count in status_counts.items():
                print(f"  {status}: {count}")
            
            print("\n📋 最近的任务:")
            recent_items = sorted(queue, key=lambda x: x.get("added_time", ""), reverse=True)[:10]
            for item in recent_items:
                status_icon = {"pending": "⏳", "processing": "🔄", "completed": "✅", "failed": "❌"}.get(item.get("status"), "❓")
                print(f"  {status_icon} {item['folder']} - {item.get('status', 'unknown')}")
        
        else:
            # 运行处理器
            processor.run_processor()
    
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
        return 130
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 