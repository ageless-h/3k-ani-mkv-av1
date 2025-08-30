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
from .modelscope_manager import ModelScopeManager
from .utils import setup_logging, check_disk_space, load_file_list

# 移除已弃用的NAS网络工具
_NAS_AVAILABLE = False

__all__ = [
    'AnimationProcessor',
    'VideoProcessor',
    'ImageProcessor',
    'ArchiveManager',
    'ModelScopeManager',
    'setup_logging',
    'check_disk_space',
    'load_file_list'
]

# NAS模式已弃用，推荐使用ModelScope模式 