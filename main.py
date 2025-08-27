#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from config import Config
from utils import (
    setup_logging, load_video_list, save_progress, load_progress,
    check_free_space, get_disk_usage, is_video_file, sanitize_filename
)
from video_processor import VideoProcessor
from image_processor import ImageProcessor
from archive_manager import ArchiveManager
from network_utils import NASConnector, LocalProcessor

class AnimationProcessor:
    def __init__(self):
        self.config = Config()
        self.config.ensure_dirs()
        
        # 设置日志
        log_file = os.path.join(self.config.TEMP_DIR, "animation_processor.log")
        self.logger = setup_logging(log_file)
        
        # 初始化处理器
        self.video_processor = VideoProcessor(self.logger)
        self.image_processor = ImageProcessor(self.logger)
        self.archive_manager = ArchiveManager(self.logger)
        
        # 初始化网络连接器
        self.nas_connector = NASConnector(logger=self.logger)
        self.local_processor = LocalProcessor(self.nas_connector, self.logger)
        
        # 进度文件
        self.progress_file = os.path.join(self.config.TEMP_DIR, "progress.json")
        self.progress = load_progress(self.progress_file)
        
        self.logger.info("AnimationProcessor初始化完成")
    
    def organize_videos_by_series(self, video_files: List[str]) -> Dict[str, List[str]]:
        """按系列组织视频文件"""
        series_dict = {}
        
        for video_path in video_files:
            # 从路径中提取系列名称（第一级子目录）
            try:
                rel_path = os.path.relpath(video_path, self.config.SOURCE_DIR)
                series_name = rel_path.split(os.sep)[0]
                
                if series_name not in series_dict:
                    series_dict[series_name] = []
                
                series_dict[series_name].append(video_path)
                
            except Exception as e:
                self.logger.warning(f"无法确定系列名称: {video_path}, {str(e)}")
        
        # 排序
        for series_name in series_dict:
            series_dict[series_name].sort()
        
        self.logger.info(f"发现 {len(series_dict)} 个系列")
        for series_name, videos in series_dict.items():
            self.logger.info(f"  {series_name}: {len(videos)} 个视频")
        
        return series_dict
    
    def determine_batch_strategy(self, series_name: str, video_count: int) -> Dict:
        """确定批处理策略"""
        if video_count <= self.config.MAX_EPISODES_PER_BATCH:
            return {
                'is_multi_batch': False,
                'batch_number': 1,
                'total_batches': 1,
                'batch_size': video_count
            }
        else:
            total_batches = (video_count + self.config.MAX_EPISODES_PER_BATCH - 1) // self.config.MAX_EPISODES_PER_BATCH
            return {
                'is_multi_batch': True,
                'batch_number': 1,  # 当前批次，会在处理时更新
                'total_batches': total_batches,
                'batch_size': self.config.MAX_EPISODES_PER_BATCH
            }
    
    def process_video_batch(self, video_files: List[str], temp_images_dir: str, 
                          frame_counter: int) -> Tuple[List[str], int]:
        """处理一批视频文件"""
        all_frames = []
        current_counter = frame_counter
        
        # 创建本地视频缓存目录
        local_video_dir = os.path.join(temp_images_dir, "videos")
        os.makedirs(local_video_dir, exist_ok=True)
        
        for video_path in tqdm(video_files, desc="处理视频"):
            try:
                self.logger.info(f"处理视频: {video_path}")
                
                # 检查视频是否已处理
                video_key = os.path.relpath(video_path, self.config.SOURCE_DIR)
                if video_key in self.progress.get('processed_videos', []):
                    self.logger.info(f"视频已处理，跳过: {video_path}")
                    continue
                
                # 先下载视频到本地
                local_video_path = self.download_video_to_local(video_path, local_video_dir)
                if not local_video_path:
                    self.logger.error(f"视频下载失败，跳过: {video_path}")
                    continue
                
                # 使用本地路径提取帧
                frames = self.video_processor.extract_all_frames(local_video_path, temp_images_dir)
                
                if frames:
                    # 处理图像
                    processed_frames = self.image_processor.batch_process_images(
                        frames, temp_images_dir, current_counter
                    )
                    
                    if processed_frames:
                        all_frames.extend(processed_frames)
                        current_counter += len(processed_frames)
                        
                        # 清理原始帧
                        for frame in frames:
                            try:
                                if os.path.exists(frame):
                                    os.remove(frame)
                            except:
                                pass
                    
                    # 记录进度
                    if 'processed_videos' not in self.progress:
                        self.progress['processed_videos'] = []
                    self.progress['processed_videos'].append(video_key)
                    save_progress(self.progress_file, self.progress)
                    
                    self.logger.info(f"视频处理完成: {video_path}, 提取 {len(processed_frames)} 帧")
                else:
                    self.logger.warning(f"未能从视频提取帧: {video_path}")
                
                # 清理本地视频文件
                try:
                    if os.path.exists(local_video_path):
                        os.remove(local_video_path)
                        self.logger.debug(f"清理本地视频: {local_video_path}")
                except Exception as e:
                    self.logger.warning(f"清理本地视频失败: {str(e)}")
                
                # 检查磁盘空间
                if not check_free_space(self.config.TEMP_DIR, self.config.MIN_FREE_SPACE_GB):
                    self.logger.warning("磁盘空间不足，停止当前批次")
                    break
                    
            except Exception as e:
                self.logger.error(f"处理视频出错 {video_path}: {str(e)}")
        
        return all_frames, current_counter
    
    def download_video_to_local(self, remote_video_path: str, local_dir: str) -> str:
        """下载视频文件到本地"""
        try:
            video_filename = os.path.basename(remote_video_path)
            local_video_path = os.path.join(local_dir, video_filename)
            
            # 如果本地已存在，直接返回
            if os.path.exists(local_video_path):
                self.logger.debug(f"本地视频已存在: {local_video_path}")
                return local_video_path
            
            # 检查远程文件是否存在
            if not self.nas_connector.check_remote_file_exists(remote_video_path):
                self.logger.error(f"远程视频文件不存在: {remote_video_path}")
                return None
            
            # 获取文件大小信息
            file_size = self.nas_connector.get_file_size(remote_video_path)
            if file_size > 0:
                file_size_mb = file_size / (1024 * 1024)
                self.logger.info(f"开始下载视频: {video_filename} ({file_size_mb:.1f} MB)")
            
            # 检查本地空间
            required_space_gb = (file_size / (1024**3)) + 1  # 额外1GB安全空间
            if not check_free_space(local_dir, required_space_gb):
                self.logger.error(f"本地空间不足，无法下载: {video_filename}")
                return None
            
            # 下载文件
            if self.nas_connector.copy_file_from_nas(remote_video_path, local_video_path):
                self.logger.info(f"视频下载成功: {local_video_path}")
                return local_video_path
            else:
                self.logger.error(f"视频下载失败: {remote_video_path}")
                return None
                
        except Exception as e:
            self.logger.error(f"下载视频出错: {str(e)}")
            return None
    
    def process_series(self, series_name: str, video_files: List[str]) -> bool:
        """处理单个动画系列"""
        try:
            self.logger.info(f"开始处理系列: {series_name} ({len(video_files)} 个视频)")
            
            # 检查系列是否已完成
            if series_name in self.progress.get('completed_series', []):
                self.logger.info(f"系列已完成，跳过: {series_name}")
                return True
            
            # 确定批处理策略
            batch_strategy = self.determine_batch_strategy(series_name, len(video_files))
            self.logger.info(f"批处理策略: {batch_strategy}")
            
            # 创建系列临时目录
            series_temp_dir = os.path.join(self.config.TEMP_DIR, sanitize_filename(series_name))
            os.makedirs(series_temp_dir, exist_ok=True)
            
            frame_counter = 1  # 每个系列重新开始计数
            all_series_frames = []
            
            if batch_strategy['is_multi_batch']:
                # 多批次处理
                batch_size = batch_strategy['batch_size']
                total_batches = batch_strategy['total_batches']
                
                for batch_num in range(1, total_batches + 1):
                    start_idx = (batch_num - 1) * batch_size
                    end_idx = min(start_idx + batch_size, len(video_files))
                    batch_videos = video_files[start_idx:end_idx]
                    
                    self.logger.info(f"处理批次 {batch_num}/{total_batches}: {len(batch_videos)} 个视频")
                    
                    # 创建批次临时目录
                    batch_temp_dir = os.path.join(series_temp_dir, f"batch_{batch_num:02d}")
                    os.makedirs(batch_temp_dir, exist_ok=True)
                    
                    # 处理视频批次
                    batch_frames, frame_counter = self.process_video_batch(
                        batch_videos, batch_temp_dir, frame_counter
                    )
                    
                    if batch_frames:
                        # 创建批次归档
                        batch_info = {
                            'is_multi_batch': True,
                            'batch_number': batch_num,
                            'total_batches': total_batches
                        }
                        
                        archive_path = self.archive_manager.create_series_archive(
                            series_name, batch_temp_dir, batch_info
                        )
                        
                        if archive_path:
                            self.logger.info(f"批次归档完成: {archive_path}")
                            
                            # 验证归档
                            if self.archive_manager.verify_archive(archive_path):
                                # 清理批次临时文件
                                self.archive_manager.cleanup_temp_files(batch_temp_dir)
                            else:
                                self.logger.error(f"归档验证失败: {archive_path}")
                                return False
                        else:
                            self.logger.error(f"批次归档失败: {series_name} batch {batch_num}")
                            return False
                    
                    # 检查是否需要继续
                    if not check_free_space(self.config.TEMP_DIR, self.config.MIN_FREE_SPACE_GB):
                        self.logger.warning("磁盘空间不足，暂停处理")
                        break
            
            else:
                # 单批次处理
                batch_frames, _ = self.process_video_batch(
                    video_files, series_temp_dir, frame_counter
                )
                
                if batch_frames:
                    # 创建系列归档
                    archive_path = self.archive_manager.create_series_archive(
                        series_name, series_temp_dir
                    )
                    
                    if archive_path:
                        self.logger.info(f"系列归档完成: {archive_path}")
                        
                        # 验证归档
                        if self.archive_manager.verify_archive(archive_path):
                            # 清理临时文件
                            self.archive_manager.cleanup_temp_files(series_temp_dir)
                        else:
                            self.logger.error(f"归档验证失败: {archive_path}")
                            return False
                    else:
                        self.logger.error(f"系列归档失败: {series_name}")
                        return False
            
            # 标记系列完成
            if 'completed_series' not in self.progress:
                self.progress['completed_series'] = []
            self.progress['completed_series'].append(series_name)
            save_progress(self.progress_file, self.progress)
            
            self.logger.info(f"系列处理完成: {series_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"处理系列出错 {series_name}: {str(e)}")
            return False
    
    def run(self):
        """运行主处理流程"""
        try:
            self.logger.info("开始动画处理流程")
            
            # 检查网络连接
            self.logger.info("检查NAS网络连接...")
            connection_ok = self.nas_connector.test_connection()
            
            # 检查tailscale状态
            devices = self.nas_connector.check_tailscale_status()
            if devices:
                self.logger.info(f"Tailscale连接正常，发现设备: {list(devices.keys())}")
                if not connection_ok:
                    self.logger.info("虽然网络测试失败，但tailscale状态正常，尝试继续运行...")
                    connection_ok = True
            
            if not connection_ok:
                self.logger.warning("网络连接测试失败，但程序将继续运行")
                self.logger.info("如果视频下载失败，请检查网络连接或SSH配置")
            
            # 加载视频文件列表
            if os.path.exists(self.config.FILELIST_PATH):
                video_files = load_video_list(self.config.FILELIST_PATH)
                self.logger.info(f"从文件列表加载 {len(video_files)} 个视频")
            else:
                # 扫描源目录
                self.logger.info(f"扫描源目录: {self.config.SOURCE_DIR}")
                video_files = []
                for root, dirs, files in os.walk(self.config.SOURCE_DIR):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if is_video_file(file_path):
                            video_files.append(file_path)
                
                self.logger.info(f"扫描发现 {len(video_files)} 个视频文件")
            
            if not video_files:
                self.logger.warning("未找到视频文件")
                return
            
            # 按系列组织
            series_dict = self.organize_videos_by_series(video_files)
            
            # 处理每个系列
            for series_name, series_videos in series_dict.items():
                self.logger.info(f"处理系列: {series_name}")
                
                # 检查磁盘空间
                disk_info = get_disk_usage(self.config.TEMP_DIR)
                self.logger.info(f"当前磁盘使用情况: {disk_info['free']:.2f} GB 可用")
                
                if disk_info['free'] < self.config.MIN_FREE_SPACE_GB * 2:
                    self.logger.warning("磁盘空间不足，停止处理")
                    break
                
                # 处理系列
                success = self.process_series(series_name, series_videos)
                
                if success:
                    self.logger.info(f"系列处理成功: {series_name}")
                else:
                    self.logger.error(f"系列处理失败: {series_name}")
                    # 继续处理下一个系列
            
            self.logger.info("动画处理流程完成")
            
        except Exception as e:
            self.logger.error(f"主流程出错: {str(e)}")
            raise
        
        finally:
            # 清理残留的临时文件
            try:
                self.archive_manager.cleanup_temp_files(self.config.TEMP_DIR)
            except Exception as e:
                self.logger.error(f"清理临时文件出错: {str(e)}")

def main():
    """主入口函数"""
    try:
        processor = AnimationProcessor()
        processor.run()
        
    except KeyboardInterrupt:
        print("\n用户中断处理")
        sys.exit(1)
    except Exception as e:
        print(f"程序出错: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 