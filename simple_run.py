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
        # 创建统一的logger
        self.logger = setup_logging('simple_system')
        
        # 初始化组件 - 不传递logger避免重复日志
        self.monitor = SimpleVideoMonitor()
        self.worker = SimpleVideoWorker()
        
        # 禁用组件的重复日志
        self.monitor.logger.disabled = True
        self.worker.logger.disabled = True
        self.worker.video_processor.logger.disabled = True
        
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
    
    def run_system(self, initialize_first: bool = True):
        """运行完整系统"""
        try:
            self.logger.info("=" * 60)
            self.logger.info("🎯 简化视频处理系统启动")
            self.logger.info("=" * 60)
            
            # 初始化队列
            if initialize_first:
                if not self.initialize_queue():
                    self.logger.error("系统初始化失败，退出")
                    return
            
            # 设置运行标志
            self.running = True
            
            # 启动监控和处理线程
            self.start_monitor()
            self.start_worker()
            
            self.logger.info("🚀 系统启动完成!")
            self.logger.info("📝 按 Ctrl+C 停止系统")
            
            # 主循环 - 定期显示状态
            try:
                while self.running:
                    time.sleep(60)  # 每分钟显示一次状态
                    status = self.monitor.get_queue_status()
                    
                    if status['queue_size'] > 0 or status['processed_count'] > 0:
                        self.logger.info(f"📊 系统状态: {status['processed_count']} 已完成, {status['queue_size']} 待处理")
                    
            except KeyboardInterrupt:
                self.logger.info("接收到停止信号...")
            
        except Exception as e:
            self.logger.error(f"系统异常: {e}")
        
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
    parser = argparse.ArgumentParser(description="简化视频处理系统")
    parser.add_argument("--no-init", action="store_true", help="跳过初始化队列，只处理新增视频")
    parser.add_argument("--status", action="store_true", help="显示系统状态")
    parser.add_argument("--init-only", action="store_true", help="只初始化队列，不启动处理")
    
    args = parser.parse_args()
    
    system = SimpleVideoSystem()
    
    if args.status:
        system.show_status()
    elif args.init_only:
        system.initialize_queue()
    else:
        # 正常运行模式
        initialize_first = not args.no_init
        system.run_system(initialize_first)


if __name__ == "__main__":
    main() 