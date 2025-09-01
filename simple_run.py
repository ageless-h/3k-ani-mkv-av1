#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化视频处理系统 - 主运行脚本
集成监控和处理功能，实现单文件视频处理流水线
"""

import os
import sys
import time
import threading
import argparse
from datetime import datetime

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from tools.simple_monitor import SimpleVideoMonitor
from tools.simple_processor import SimpleVideoWorker
from src.utils import setup_logging


class SimpleVideoSystem:
    """简化视频处理系统"""
    
    def __init__(self):
        # 创建主系统logger
        self.logger = setup_logging('simple_system')
        
        # 初始化组件（每个组件有自己的logger名称）
        self.monitor = SimpleVideoMonitor()
        self.worker = SimpleVideoWorker()
        
        # 线程控制
        self.running = False
        self.monitor_thread = None
        self.worker_thread = None
    
    def initialize_queue(self) -> bool:
        """初始化处理队列"""
        self.logger.info("🚀 初始化视频处理队列...")
        
        try:
            # 从现有仓库扫描所有视频
            success = self.monitor.initialize_from_existing()
            
            if success:
                status = self.monitor.get_queue_status()
                self.logger.info(f"✅ 队列初始化成功!")
                self.logger.info(f"📊 队列状态: {status['queue_size']} 个待处理视频")
                
                # 显示前几个待处理的视频
                if status['next_videos']:
                    self.logger.info("📋 即将处理的视频:")
                    for i, video in enumerate(status['next_videos'][:3], 1):
                        size_mb = video.get('size', 0) // 1024 // 1024
                        self.logger.info(f"  {i}. {video['path']} ({size_mb} MB)")
                
                return True
            else:
                self.logger.warning("⚠️  队列初始化完成，但没有发现新视频")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ 队列初始化失败: {e}")
            return False
    
    def start_monitor(self):
        """启动监控线程"""
        def monitor_worker():
            self.logger.info("👁️  启动视频监控器...")
            try:
                while self.running:
                    # 执行一次监控检查
                    new_count = self.monitor.monitor_once()
                    
                    if new_count > 0:
                        self.logger.info(f"🆕 发现 {new_count} 个新视频")
                    
                    # 等待5分钟后再次检查
                    for _ in range(300):  # 5分钟 = 300秒
                        if not self.running:
                            break
                        time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"监控器异常: {e}")
        
        self.monitor_thread = threading.Thread(target=monitor_worker, daemon=True)
        self.monitor_thread.start()
    
    def start_worker(self):
        """启动处理线程"""
        def worker_runner():
            self.logger.info("🔧 启动视频处理器...")
            try:
                while self.running:
                    # 获取下一个要处理的视频
                    next_video = self.monitor.get_next_video()
                    
                    if next_video:
                        # 处理视频
                        self.logger.info(f"🎬 开始处理: {next_video['path']}")
                        success = self.worker.process_single_video(next_video)
                        
                        if success:
                            self.logger.info(f"✅ 处理成功: {next_video['path']}")
                        else:
                            self.logger.error(f"❌ 处理失败: {next_video['path']}")
                            # 失败的视频标记为已处理，避免死循环
                            self.monitor.mark_video_processed(next_video['path'])
                        
                        # 显示进度
                        status = self.monitor.get_queue_status()
                        self.logger.info(f"📊 进度: {status['processed_count']} 已完成, {status['queue_size']} 待处理")
                    
                    else:
                        # 队列为空，等待30秒
                        self.logger.debug("队列为空，等待新视频...")
                        for _ in range(30):
                            if not self.running:
                                break
                            time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"处理器异常: {e}")
        
        self.worker_thread = threading.Thread(target=worker_runner, daemon=True)
        self.worker_thread.start()
    
    def run_system(self, mode='full'):
        """运行系统"""
        self.logger.info(f"🚀 启动简化视频处理系统 (模式: {mode})")
        
        try:
            if mode in ['full', 'init-only']:
                # 初始化阶段
                self.logger.info("📊 初始化阶段...")
                if not self.monitor.initialize_from_existing():
                    self.logger.warning("⚠️ 初始化未发现新视频")
                else:
                    self.logger.info("✅ 初始化完成")
                
                if mode == 'init-only':
                    status = self.monitor.get_queue_status()
                    self.logger.info(f"📈 队列状态: {status['queue_size']} 待处理, {status['processed_count']} 已完成")
                    return
            
            # 启动工作线程
            self.running = True
            
            if mode in ['full', 'no-init']:
                # 启动监控线程
                self.monitor_thread = threading.Thread(target=self._run_monitor, daemon=True)
                self.monitor_thread.start()
                self.logger.info("📡 监控线程已启动")
                
                # 启动工作线程  
                self.worker_thread = threading.Thread(target=self._run_worker, daemon=True)
                self.worker_thread.start()
                self.logger.info("⚙️ 工作线程已启动")
            
            # 主循环 - 定期显示状态
            last_status_time = time.time()
            while self.running:
                time.sleep(10)  # 每10秒检查一次
                
                # 每60秒显示一次详细状态
                current_time = time.time()
                if current_time - last_status_time >= 60:
                    status = self.monitor.get_queue_status()
                    self.logger.info(f"📊 系统状态: {status['processed_count']} 已完成, {status['queue_size']} 待处理")
                    if status['next_videos']:
                        next_video = status['next_videos'][0]['path'] if status['next_videos'] else "无"
                        self.logger.info(f"🎯 下一个视频: {next_video}")
                    last_status_time = current_time
                
        except KeyboardInterrupt:
            self.logger.info("🛑 系统停止中...")
        except Exception as e:
            self.logger.error(f"💥 系统异常: {e}")
        finally:
            self.stop_system()
    
    def stop_system(self):
        """停止系统"""
        self.logger.info("🛑 正在停止系统...")
        self.running = False
        
        # 等待线程结束
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=10)
        
        self.logger.info("✅ 系统已停止")
    
    def show_status(self):
        """显示系统状态"""
        self.logger.info("📊 系统状态:")
        status = self.monitor.get_queue_status()
        
        self.logger.info(f"  已处理视频: {status['processed_count']}")
        self.logger.info(f"  待处理视频: {status['queue_size']}")
        
        if status['next_videos']:
            self.logger.info("  即将处理的视频:")
            for i, video in enumerate(status['next_videos'][:5], 1):
                size_mb = video.get('size', 0) // 1024 // 1024
                self.logger.info(f"    {i}. {video['path']} ({size_mb} MB)")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='简化视频处理系统')
    parser.add_argument('--mode', choices=['full', 'no-init', 'init-only', 'status'], 
                       default='full', help='运行模式')
    
    args = parser.parse_args()
    
    system = SimpleVideoSystem()
    
    if args.mode == 'status':
        # 只显示状态
        status = system.monitor.get_queue_status()
        print(f"📊 队列状态: {status['queue_size']} 待处理, {status['processed_count']} 已完成")
        if status['next_videos']:
            print("🎯 下一批视频:")
            for i, video in enumerate(status['next_videos'][:5], 1):
                print(f"  {i}. {video['path']}")
    else:
        system.run_system(args.mode)


if __name__ == "__main__":
    main() 