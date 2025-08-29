"""
3K Animation MKV-AV1 Processing System

A comprehensive system for processing animation videos:
- Convert videos to MKV+AV1 format
- Extract scene frames using PySceneDetect
- Compress images to WebP format
- Archive processed data
"""

__version__ = "1.0.0"
__author__ = "ageless-h"

# 导入主要模块
from .main import AnimationProcessor
from .video_processor import VideoProcessor
from .image_processor import ImageProcessor
from .archive_manager import ArchiveManager
from .network_utils import NASConnector
from .utils import setup_logging, check_disk_space, load_file_list

__all__ = [
    'AnimationProcessor',
    'VideoProcessor', 
    'ImageProcessor',
    'ArchiveManager',
    'NASConnector',
    'setup_logging',
    'check_disk_space',
    'load_file_list'
] 