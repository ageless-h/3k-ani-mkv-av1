# -*- coding: utf-8 -*-
"""
简化版动画处理系统包初始化
"""

# 只导入简化系统需要的基础组件
from .utils import setup_logging, check_free_space, load_video_list
from .simple_processor import SimpleVideoProcessor

# 可选导入ModelScope管理器（如果需要的话）
try:
    from .modelscope_manager import ModelScopeManager
    _MODELSCOPE_AVAILABLE = True
except ImportError:
    _MODELSCOPE_AVAILABLE = False

__all__ = [
    'SimpleVideoProcessor',
    'setup_logging',
    'check_free_space', 
    'load_video_list'
]

if _MODELSCOPE_AVAILABLE:
    __all__.append('ModelScopeManager') 