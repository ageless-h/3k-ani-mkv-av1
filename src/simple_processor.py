#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化视频处理器
专门用于单文件 MP4→MKV+AV1 转换
"""

import os
import logging
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Optional

from config.config import Config


class SimpleVideoProcessor:
    """简化的视频处理器 - 只做格式转换"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.config = Config()
    
    def convert_to_mkv_av1(self, input_path: str, output_path: str) -> bool:
        """
        将视频转换为MKV+AV1格式
        
        Args:
            input_path: 输入视频文件路径
            output_path: 输出MKV文件路径
            
        Returns:
            bool: 转换是否成功
        """
        try:
            self.logger.info(f"开始转换: {os.path.basename(input_path)}")
            
            # 构建FFmpeg命令
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-c:v', 'av1_nvenc',  # 使用NVIDIA硬件编码
                '-preset', 'p4',      # 平衡质量和速度
                '-rc', 'vbr',         # 可变比特率
                '-cq', '28',          # 质量控制
                '-b:v', '0',          # 让CQ控制比特率
                '-maxrate', '10M',    # 最大比特率限制
                '-bufsize', '20M',    # 缓冲区大小
                '-c:a', 'copy',       # 音频直接复制
                '-c:s', 'copy',       # 字幕直接复制
                '-map', '0',          # 复制所有流
                '-avoid_negative_ts', 'make_zero',
                '-y',                 # 覆盖输出文件
                output_path
            ]
            
            self.logger.info(f"FFmpeg命令: {' '.join(cmd)}")
            
            # 执行转换
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1小时超时
            )
            
            if result.returncode == 0:
                # 检查输出文件是否存在且有内容
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    input_size = os.path.getsize(input_path)
                    output_size = os.path.getsize(output_path)
                    compression_ratio = (1 - output_size / input_size) * 100
                    
                    self.logger.info(f"转换成功: {os.path.basename(input_path)}")
                    self.logger.info(f"压缩比: {compression_ratio:.1f}% "
                                   f"({input_size // 1024 // 1024}MB → {output_size // 1024 // 1024}MB)")
                    return True
                else:
                    self.logger.error(f"输出文件无效: {output_path}")
                    return False
            else:
                self.logger.error(f"FFmpeg转换失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"转换超时: {os.path.basename(input_path)}")
            return False
        except Exception as e:
            self.logger.error(f"转换异常: {e}")
            return False
    
    def get_output_filename(self, input_filename: str) -> str:
        """
        根据输入文件名生成输出文件名
        保留原始前缀，只改变扩展名
        
        Args:
            input_filename: 输入文件名
            
        Returns:
            str: 输出文件名
        """
        # 移除原扩展名，添加.mkv
        base_name = os.path.splitext(input_filename)[0]
        return f"{base_name}.mkv"
    
    def process_single_video(self, input_path: str, temp_dir: str) -> Optional[str]:
        """
        处理单个视频文件
        
        Args:
            input_path: 输入视频文件路径
            temp_dir: 临时目录
            
        Returns:
            Optional[str]: 成功时返回输出文件路径，失败时返回None
        """
        try:
            input_filename = os.path.basename(input_path)
            output_filename = self.get_output_filename(input_filename)
            output_path = os.path.join(temp_dir, output_filename)
            
            self.logger.info(f"处理视频: {input_filename} → {output_filename}")
            
            # 执行转换
            if self.convert_to_mkv_av1(input_path, output_path):
                return output_path
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"处理视频失败: {e}")
            return None
    
    def cleanup_temp_files(self, *file_paths):
        """清理临时文件"""
        for file_path in file_paths:
            try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                    self.logger.debug(f"清理临时文件: {file_path}")
            except Exception as e:
                self.logger.warning(f"清理文件失败 {file_path}: {e}") 