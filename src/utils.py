import os
import shutil
import logging
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

def setup_logging(log_file: str = None) -> logging.Logger:
    """设置日志系统"""
    logger = logging.getLogger('animation_processor')
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def get_disk_usage(path: str) -> Dict[str, float]:
    """获取磁盘使用情况（GB）"""
    stat = shutil.disk_usage(path)
    return {
        'total': stat.total / (1024**3),
        'used': stat.used / (1024**3),
        'free': stat.free / (1024**3)
    }

def check_free_space(path: str, min_gb: float) -> bool:
    """检查是否有足够的磁盘空间"""
    usage = get_disk_usage(path)
    return usage['free'] >= min_gb

def load_video_list(file_path: str) -> List[str]:
    """从文件加载视频文件列表"""
    if not os.path.exists(file_path):
        return []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def save_progress(progress_file: str, data: Dict[str, Any]):
    """保存处理进度"""
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_progress(progress_file: str) -> Dict[str, Any]:
    """加载处理进度"""
    if not os.path.exists(progress_file):
        return {}
    
    try:
        with open(progress_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def get_video_extensions() -> List[str]:
    """获取支持的视频文件扩展名"""
    return ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v']

def is_video_file(file_path: str) -> bool:
    """检查文件是否为视频文件"""
    return Path(file_path).suffix.lower() in get_video_extensions()

def sanitize_filename(filename: str) -> str:
    """清理文件名，移除非法字符"""
    illegal_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in illegal_chars:
        filename = filename.replace(char, '_')
    return filename

def format_time(seconds: float) -> str:
    """格式化时间为可读格式"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def create_backup(file_path: str) -> str:
    """创建文件备份"""
    backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(file_path, backup_path)
    return backup_path 