#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from pathlib import Path

class ModelScopeConfig:
    """魔搭社区配置"""
    
    # 魔搭API配置
    MODELSCOPE_TOKEN = "ms-30a739b2-842b-4fe7-8485-ab9b5114afb5"
    
    # 数据集仓库配置
    REPOSITORIES = {
        'input': 'ageless/3k-animation-mkv-av1',              # 输入视频仓库
        'output_mkv': 'ageless/3k-animation-mkv-av1-output',   # MKV输出仓库
        'output_webp': 'ageless/3k-animation-mkv-av1-output-webp'  # WebP输出仓库
    }
    
    # 本地路径配置
    BASE_DIR = "/tmp/3k_animation_processing"
    
    # 魔搭缓存和工作目录
    MODELSCOPE_CACHE_DIR = os.path.join(BASE_DIR, "modelscope_cache")
    DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
    PROCESSING_DIR = os.path.join(BASE_DIR, "processing")
    
    # 输出目录
    OUTPUT_DIR = "/root/output/animation"
    VIDEO_OUTPUT_DIR = "/root/output/video" 
    TEMP_DIR = "/tmp/animation_temp"
    
    # 批处理配置
    DOWNLOAD_BATCH_SIZE = 20        # 每批下载的视频数量
    MAX_EPISODES_PER_BATCH = 30     # 每批处理的剧集数量
    MIN_FREE_SPACE_GB = 10          # 最小保留空间 (GB)
    
    # 网络配置
    DOWNLOAD_TIMEOUT = 300          # 下载超时时间 (秒)
    UPLOAD_TIMEOUT = 600            # 上传超时时间 (秒)
    MAX_RETRY_COUNT = 3             # 最大重试次数
    
    # 并发配置
    MAX_DOWNLOAD_WORKERS = 4        # 最大下载并发数
    MAX_UPLOAD_WORKERS = 2          # 最大上传并发数
    MAX_PROCESSING_WORKERS = 2      # 最大处理并发数
    
    # 视频处理配置
    VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm']
    
    # 文件大小限制
    MAX_SINGLE_FILE_SIZE_GB = 5     # 单个文件最大大小
    MAX_BATCH_SIZE_GB = 50          # 单批最大大小
    
    # 魔搭上传配置
    UPLOAD_CHUNK_SIZE_MB = 10       # 分块上传大小
    ENABLE_PROGRESS_BAR = True      # 启用进度条
    
    @staticmethod
    def ensure_dirs():
        """确保必要的目录存在"""
        dirs_to_create = [
            ModelScopeConfig.BASE_DIR,
            ModelScopeConfig.MODELSCOPE_CACHE_DIR,
            ModelScopeConfig.DOWNLOAD_DIR,
            ModelScopeConfig.UPLOAD_DIR,
            ModelScopeConfig.PROCESSING_DIR,
            ModelScopeConfig.OUTPUT_DIR,
            ModelScopeConfig.VIDEO_OUTPUT_DIR,
            ModelScopeConfig.TEMP_DIR
        ]
        
        for dir_path in dirs_to_create:
            os.makedirs(dir_path, exist_ok=True)
    
    @staticmethod
    def get_repo_url(repo_type: str) -> str:
        """获取仓库URL"""
        repo_id = ModelScopeConfig.REPOSITORIES.get(repo_type)
        if not repo_id:
            raise ValueError(f"未知的仓库类型: {repo_type}")
        return f"https://www.modelscope.cn/datasets/{repo_id}"
    
    @staticmethod
    def validate_token() -> bool:
        """验证Token格式"""
        token = ModelScopeConfig.MODELSCOPE_TOKEN
        return token and token.startswith('ms-') and len(token) > 10
    
    @staticmethod
    def get_download_command(repo_type: str, file_path: str, local_dir: str) -> list:
        """生成下载命令"""
        repo_id = ModelScopeConfig.REPOSITORIES[repo_type]
        
        return [
            "modelscope", "download",
            repo_id,
            file_path,
            "--cache_dir", ModelScopeConfig.MODELSCOPE_CACHE_DIR,
            "--local_dir", local_dir
        ]
    
    @staticmethod
    def get_upload_params(repo_type: str) -> dict:
        """获取上传参数"""
        repo_id = ModelScopeConfig.REPOSITORIES[repo_type]
        
        return {
            'repo_id': repo_id,
            'repo_type': 'dataset',
            'token': ModelScopeConfig.MODELSCOPE_TOKEN
        } 