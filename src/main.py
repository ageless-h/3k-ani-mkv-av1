#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import Config
from src.utils import (
    setup_logging, load_video_list, save_progress, load_progress,
    check_free_space, get_disk_usage, is_video_file, sanitize_filename
)
from src.video_processor import VideoProcessor
from src.image_processor import ImageProcessor
from src.archive_manager import ArchiveManager
from src.modelscope_manager import ModelScopeManager

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
        
        # 初始化魔搭管理器
        if self.config.DEPLOYMENT_MODE == "modelscope":
            self.modelscope_manager = ModelScopeManager(
                token=self.config.MODELSCOPE_TOKEN,
                logger=self.logger
            )
        else:
            self.modelscope_manager = None
        
        # 进度文件
        self.progress_file = os.path.join(self.config.TEMP_DIR, "progress.json")
        self.progress = load_progress(self.progress_file)
        
        self.logger.info("AnimationProcessor初始化完成")
    
    def organize_videos_by_series(self, video_files: List[str]) -> Dict[str, List[str]]:
        """按系列组织视频文件"""
        series_dict = {}
        
        for video_path in video_files:
            # 从路径中提取系列名称
            # 假设路径格式: /volume1/db/5_video/archive/动画系列名/视频文件
            path_parts = video_path.strip('/').split('/')
            
            if len(path_parts) >= 2:
                series_name = path_parts[-2]  # 倒数第二个部分作为系列名
            else:
                series_name = "未分类"
                
                if series_name not in series_dict:
                    series_dict[series_name] = []
                series_dict[series_name].append(video_path)
        
        # 按系列大小排序，优先处理小系列
        series_dict = dict(sorted(series_dict.items(), key=lambda x: len(x[1])))
        
        self.logger.info(f"发现 {len(series_dict)} 个动画系列")
        for series, videos in series_dict.items():
            self.logger.info(f"  {series}: {len(videos)} 个视频")
        
        return series_dict
    
    def process_videos_in_batch(self, video_paths: List[str], batch_name: str) -> bool:
        """
        使用魔搭社区处理视频批次的新流程:
        1. 从魔搭下载视频
        2. 本地处理
        3. 上传结果到魔搭
        4. 清理本地文件
        """
        try:
            self.logger.info(f"开始处理批次: {batch_name}, 共 {len(video_paths)} 个视频")
            
            # 步骤1: 从魔搭下载视频
            self.logger.info("步骤1: 从魔搭社区下载视频...")
            downloaded_files = self.modelscope_manager.download_video_batch(
                video_paths, batch_name
            )
            
            if not downloaded_files:
                self.logger.error(f"批次 {batch_name} 无视频下载成功")
                return False
            
            self.logger.info(f"成功下载 {len(downloaded_files)} 个视频文件")
            
            # 步骤2: 本地处理视频
            self.logger.info("步骤2: 本地处理视频...")
            
            # 创建处理目录
            batch_processing_dir = os.path.join(self.config.TEMP_DIR, f"batch_{batch_name}")
            batch_images_dir = os.path.join(batch_processing_dir, "images")
            batch_mkv_dir = os.path.join(batch_processing_dir, "mkv")
            
            os.makedirs(batch_images_dir, exist_ok=True)
            os.makedirs(batch_mkv_dir, exist_ok=True)
            
            # 处理所有下载的视频
            all_processed_frames = []
            frame_counter = 1
            
            for original_path, local_video_path in downloaded_files.items():
                try:
                    self.logger.info(f"处理视频: {os.path.basename(local_video_path)}")
                    
                    # 视频转换为MKV+AV1
                    mkv_output_path = self.convert_to_mkv_av1(local_video_path, batch_mkv_dir)
                    
                    # 提取帧并处理图像
                    frames = self.video_processor.extract_all_frames(
                        local_video_path, batch_images_dir
                    )
                    
                    if frames:
                        processed_frames = self.image_processor.batch_process_images(
                            frames, batch_images_dir, frame_counter
                    )
                    
                    if processed_frames:
                            all_processed_frames.extend(processed_frames)
                            frame_counter += len(processed_frames)
                        
                        # 清理原始帧
                        for frame in frames:
                            try:
                                if os.path.exists(frame):
                                    os.remove(frame)
                            except:
                                pass
                    
                    self.logger.info(f"视频处理完成: {os.path.basename(local_video_path)}")
                
                except Exception as e:
                    self.logger.error(f"处理视频失败 {local_video_path}: {e}")
                    continue
            
            # 步骤3: 创建压缩包
            if all_processed_frames:
                self.logger.info("步骤3: 创建WebP压缩包...")
                
                archive_path = self.archive_manager.create_archive(
                    all_processed_frames, 
                    self.config.OUTPUT_DIR,
                    f"{batch_name}_webp"
                )
                
                if archive_path:
                    self.logger.info(f"压缩包创建成功: {archive_path}")
                    
                    # 步骤4: 上传结果到魔搭
                    self.logger.info("步骤4: 上传结果到魔搭社区...")
                    
                    # 上传MKV结果
                    if os.path.exists(batch_mkv_dir) and os.listdir(batch_mkv_dir):
                        mkv_success = self.modelscope_manager.upload_mkv_results(
                            batch_mkv_dir, batch_name
                        )
                        if mkv_success:
                            self.logger.info("MKV结果上传成功")
                        else:
                            self.logger.error("MKV结果上传失败")
                    
                    # 上传WebP压缩包
                    webp_success = self.modelscope_manager.upload_webp_archive(
                        archive_path, batch_name
                    )
                    
                    if webp_success:
                        self.logger.info("WebP压缩包上传成功")
                        
                        # 步骤5: 清理本地文件
                        self.logger.info("步骤5: 清理本地文件...")
                        self.cleanup_batch_files(batch_processing_dir, archive_path)
                        self.modelscope_manager.cleanup_downloads(batch_name)
                        
                        return True
                    else:
                        self.logger.error("WebP压缩包上传失败")
                        return False
                else:
                    self.logger.error("压缩包创建失败")
                    return False
            else:
                self.logger.warning(f"批次 {batch_name} 没有生成有效的处理结果")
                return False
        
        except Exception as e:
            self.logger.error(f"批次处理失败 {batch_name}: {e}")
            return False
    
    def convert_to_mkv_av1(self, input_video_path: str, output_dir: str) -> str:
        """转换视频为MKV+AV1格式"""
        try:
            video_name = os.path.splitext(os.path.basename(input_video_path))[0]
            output_path = os.path.join(output_dir, f"{video_name}_av1.mkv")
            
            # 调用视频处理器进行转换
            success = self.video_processor.convert_to_av1(input_video_path, output_path)
            
            if success and os.path.exists(output_path):
                self.logger.info(f"视频转换成功: {output_path}")
                return output_path
            else:
                self.logger.error(f"视频转换失败: {input_video_path}")
                return None
        
        except Exception as e:
            self.logger.error(f"视频转换出错: {e}")
            return None
    
    def cleanup_batch_files(self, batch_dir: str, archive_path: str = None):
        """清理批次处理文件"""
        try:
            # 清理处理目录
            if os.path.exists(batch_dir):
                import shutil
                shutil.rmtree(batch_dir)
                self.logger.info(f"已清理批次目录: {batch_dir}")
            
            # 清理本地压缩包（可选）
            if archive_path and os.path.exists(archive_path):
                os.remove(archive_path)
                self.logger.info(f"已清理本地压缩包: {archive_path}")
            
        except Exception as e:
            self.logger.warning(f"清理文件失败: {e}")
    
    def run(self):
        """主运行函数"""
        try:
            self.logger.info("="*50)
            self.logger.info("开始3K动画处理任务 (魔搭社区模式)")
            self.logger.info("="*50)
            
            # 验证魔搭连接
            if not self.modelscope_manager:
                self.logger.error("魔搭管理器未初始化")
                return False
            
            self.logger.info("验证魔搭仓库连接...")
            repos_status = self.modelscope_manager.verify_repositories()
            
            for repo_name, status in repos_status.items():
                if status:
                    self.logger.info(f"✅ {repo_name} 仓库连接正常")
                else:
                    self.logger.error(f"❌ {repo_name} 仓库连接失败")
            
            if not all(repos_status.values()):
                self.logger.error("部分仓库连接失败，请检查网络和权限")
                return False
            
            # 获取视频文件列表
            self.logger.info("获取视频文件列表...")
            video_files = self.modelscope_manager.get_available_videos()
            
            if not video_files:
                self.logger.error("未获取到视频文件列表")
                return False
            
            self.logger.info(f"获取到 {len(video_files)} 个视频文件")
            
            # 按系列组织视频
            series_dict = self.organize_videos_by_series(video_files)
            
            # 按批次处理
            batch_size = self.config.MAX_EPISODES_PER_BATCH
            total_processed = 0
            total_batches = 0
            
            for series_name, series_videos in series_dict.items():
                self.logger.info(f"开始处理系列: {series_name} ({len(series_videos)} 个视频)")
                
                # 将系列分批处理
                for i in range(0, len(series_videos), batch_size):
                    batch_videos = series_videos[i:i + batch_size]
                    batch_name = f"{sanitize_filename(series_name)}_part{(i//batch_size)+1:02d}of{(len(series_videos)-1)//batch_size+1:02d}"
                    
                    # 检查是否已处理
                    if batch_name in self.progress.get('completed_batches', []):
                        self.logger.info(f"批次已处理，跳过: {batch_name}")
                        continue
                
                # 检查磁盘空间
                    if not check_free_space(self.config.TEMP_DIR, self.config.MIN_FREE_SPACE_GB):
                        self.logger.error("磁盘空间不足，停止处理")
                    break
                
                    # 处理批次
                    success = self.process_videos_in_batch(batch_videos, batch_name)
                
                if success:
                        # 记录进度
                        if 'completed_batches' not in self.progress:
                            self.progress['completed_batches'] = []
                        self.progress['completed_batches'].append(batch_name)
                        save_progress(self.progress_file, self.progress)
                        
                        total_processed += len(batch_videos)
                        total_batches += 1
                        
                        self.logger.info(f"✅ 批次处理成功: {batch_name}")
                else:
                        self.logger.error(f"❌ 批次处理失败: {batch_name}")
                    
                    # 显示进度
                    progress_pct = (total_processed / len(video_files)) * 100
                    self.logger.info(f"总进度: {total_processed}/{len(video_files)} ({progress_pct:.1f}%)")
            
            self.logger.info("="*50)
            self.logger.info(f"处理完成! 总共处理 {total_batches} 个批次，{total_processed} 个视频")
            self.logger.info("="*50)
            
            return True
            
        except Exception as e:
            self.logger.error(f"主程序运行失败: {e}")
            return False

def main():
    """主入口函数"""
    try:
        processor = AnimationProcessor()
        success = processor.run()
        
        if success:
            print("✅ 3K动画处理任务完成!")
            return 0
        else:
            print("❌ 3K动画处理任务失败!")
            return 1
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断任务")
        return 130
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 