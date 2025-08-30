#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from tqdm import tqdm

try:
    from modelscope.hub.api import HubApi
    from modelscope import MsDataset
    MODELSCOPE_AVAILABLE = True
except ImportError:
    MODELSCOPE_AVAILABLE = False

from src.utils import setup_logging

class ModelScopeManager:
    """魔搭社区数据管理器 - 替代NAS网络传输"""
    
    def __init__(self, token: str, logger=None):
        self.token = token
        self.logger = logger or setup_logging()
        
        if not MODELSCOPE_AVAILABLE:
            raise ImportError("请安装modelscope: pip install modelscope")
        
        # 初始化API
        self.api = HubApi()
        try:
            self.api.login(self.token)
            self.logger.info("魔搭社区登录成功")
        except Exception as e:
            self.logger.error(f"魔搭社区登录失败: {e}")
            raise
        
        # 数据集配置
        self.input_repo = "ageless/3k-animation-mkv-av1"  # 输入仓库
        self.output_mkv_repo = "ageless/3k-animation-mkv-av1-output"  # MKV输出仓库
        self.output_webp_repo = "ageless/3k-animation-mkv-av1-output-webp"  # WebP输出仓库
        
        # 本地缓存目录
        self.cache_dir = "/tmp/modelscope_cache"
        self.download_dir = "/tmp/modelscope_downloads"
        self.upload_dir = "/tmp/modelscope_uploads"
        
        # 确保目录存在
        for dir_path in [self.cache_dir, self.download_dir, self.upload_dir]:
            os.makedirs(dir_path, exist_ok=True)
    
    def download_video_batch(self, video_paths: List[str], batch_name: str) -> Dict[str, str]:
        """
        批量下载视频文件
        
        Args:
            video_paths: 视频文件路径列表
            batch_name: 批次名称，用于组织下载
        
        Returns:
            Dict[str, str]: 原始路径 -> 本地路径的映射
        """
        downloaded_files = {}
        batch_dir = os.path.join(self.download_dir, batch_name)
        os.makedirs(batch_dir, exist_ok=True)
        
        self.logger.info(f"开始下载批次: {batch_name}, 共{len(video_paths)}个文件")
        
        try:
            # 使用魔搭下载API
            for video_path in tqdm(video_paths, desc="下载视频"):
                try:
                    filename = os.path.basename(video_path)
                    local_path = os.path.join(batch_dir, filename)
                    
                    # 检查文件是否已存在
                    if os.path.exists(local_path):
                        self.logger.info(f"文件已存在，跳过下载: {filename}")
                        downloaded_files[video_path] = local_path
                        continue
                    
                    # 使用modelscope CLI下载
                    repo_path = video_path.replace("/volume1/db/5_video/archive/", "")
                    
                    download_cmd = [
                        "modelscope", "download",
                        self.input_repo,
                        repo_path,
                        "--cache_dir", self.cache_dir,
                        "--local_dir", batch_dir
                    ]
                    
                    import subprocess
                    result = subprocess.run(download_cmd, capture_output=True, text=True, timeout=300)
                    
                    if result.returncode == 0 and os.path.exists(local_path):
                        downloaded_files[video_path] = local_path
                        self.logger.info(f"下载成功: {filename}")
                    else:
                        self.logger.error(f"下载失败: {filename}, 错误: {result.stderr}")
                
                except Exception as e:
                    self.logger.error(f"下载文件出错 {video_path}: {e}")
                    continue
            
            self.logger.info(f"批次下载完成: {len(downloaded_files)}/{len(video_paths)}")
            return downloaded_files
        
        except Exception as e:
            self.logger.error(f"批量下载出错: {e}")
            return downloaded_files
    
    def upload_mkv_results(self, local_mkv_dir: str, series_name: str) -> bool:
        """
        上传MKV转换结果
        
        Args:
            local_mkv_dir: 本地MKV目录
            series_name: 系列名称
        
        Returns:
            bool: 上传是否成功
        """
        try:
            self.logger.info(f"开始上传MKV结果: {series_name}")
            
            # 准备上传目录
            upload_path = os.path.join(self.upload_dir, "mkv", series_name)
            if os.path.exists(upload_path):
                shutil.rmtree(upload_path)
            shutil.copytree(local_mkv_dir, upload_path)
            
            # 上传到魔搭
            self.api.upload_folder(
                repo_id=self.output_mkv_repo,
                folder_path=upload_path,
                path_in_repo=series_name,
                commit_message=f'Upload MKV results for {series_name}',
                repo_type='dataset'
            )
            
            self.logger.info(f"MKV结果上传成功: {series_name}")
            
            # 清理临时文件
            shutil.rmtree(upload_path)
            return True
        
        except Exception as e:
            self.logger.error(f"MKV结果上传失败 {series_name}: {e}")
            return False
    
    def upload_webp_archive(self, archive_path: str, series_name: str) -> bool:
        """
        上传WebP压缩包
        
        Args:
            archive_path: 本地压缩包路径
            series_name: 系列名称
        
        Returns:
            bool: 上传是否成功
        """
        try:
            archive_name = os.path.basename(archive_path)
            self.logger.info(f"开始上传WebP压缩包: {archive_name}")
            
            # 上传单个文件到魔搭
            repo_path = f"{series_name}/{archive_name}"
            
            self.api.upload_file(
                path_or_fileobj=archive_path,
                path_in_repo=repo_path,
                repo_id=self.output_webp_repo,
                repo_type='dataset',
                commit_message=f'Upload WebP archive: {archive_name}'
            )
            
            self.logger.info(f"WebP压缩包上传成功: {archive_name}")
            return True
        
        except Exception as e:
            self.logger.error(f"WebP压缩包上传失败 {archive_path}: {e}")
            return False
    
    def cleanup_downloads(self, batch_name: str) -> None:
        """清理下载的临时文件"""
        try:
            batch_dir = os.path.join(self.download_dir, batch_name)
            if os.path.exists(batch_dir):
                shutil.rmtree(batch_dir)
                self.logger.info(f"已清理下载目录: {batch_name}")
        except Exception as e:
            self.logger.warning(f"清理下载目录失败 {batch_name}: {e}")
    
    def get_download_progress(self) -> Dict[str, Any]:
        """获取下载进度信息"""
        try:
            total_size = 0
            downloaded_size = 0
            
            if os.path.exists(self.download_dir):
                for root, dirs, files in os.walk(self.download_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            size = os.path.getsize(file_path)
                            downloaded_size += size
                        except:
                            continue
            
            return {
                "downloaded_size": downloaded_size,
                "downloaded_size_gb": round(downloaded_size / (1024**3), 2),
                "active_downloads": len(os.listdir(self.download_dir)) if os.path.exists(self.download_dir) else 0
            }
        except Exception as e:
            self.logger.error(f"获取下载进度失败: {e}")
            return {"downloaded_size": 0, "downloaded_size_gb": 0, "active_downloads": 0}
    
    def verify_repositories(self) -> Dict[str, bool]:
        """验证魔搭仓库是否可访问"""
        repos_status = {}
        
        for repo_name, repo_id in [
            ("input", self.input_repo),
            ("output_mkv", self.output_mkv_repo),
            ("output_webp", self.output_webp_repo)
        ]:
            try:
                # 尝试获取仓库信息
                import subprocess
                result = subprocess.run([
                    "modelscope", "download", repo_id, "--include", "README.md",
                    "--cache_dir", self.cache_dir
                ], capture_output=True, text=True, timeout=30)
                
                repos_status[repo_name] = result.returncode == 0
                
                if repos_status[repo_name]:
                    self.logger.info(f"仓库验证成功: {repo_id}")
                else:
                    self.logger.error(f"仓库验证失败: {repo_id}")
            
            except Exception as e:
                self.logger.error(f"仓库验证出错 {repo_id}: {e}")
                repos_status[repo_name] = False
        
        return repos_status
    
    def get_available_videos(self, limit: Optional[int] = None) -> List[str]:
        """
        获取可用的视频文件列表
        
        Args:
            limit: 限制返回的文件数量
        
        Returns:
            List[str]: 视频文件路径列表
        """
        try:
            # 从输入仓库下载文件列表
            filelist_path = os.path.join(self.cache_dir, "filelist.txt")
            
            if not os.path.exists(filelist_path):
                self.logger.info("下载视频文件列表...")
                
                download_cmd = [
                    "modelscope", "download",
                    self.input_repo,
                    "filelist.txt",
                    "--cache_dir", self.cache_dir
                ]
                
                import subprocess
                result = subprocess.run(download_cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode != 0:
                    self.logger.error(f"下载文件列表失败: {result.stderr}")
                    return []
            
            # 读取文件列表
            video_files = []
            with open(filelist_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        video_files.append(line)
            
            if limit:
                video_files = video_files[:limit]
            
            self.logger.info(f"获取到{len(video_files)}个视频文件")
            return video_files
        
        except Exception as e:
            self.logger.error(f"获取视频列表失败: {e}")
            return [] 