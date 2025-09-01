#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化视频处理器
负责单个视频的完整处理流程：下载→转换→上传→清理
"""

import os
import sys
import time
import tempfile
import subprocess
from typing import Optional, Dict
from pathlib import Path

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config.config import Config
from src.utils import setup_logging
from src.simple_processor import SimpleVideoProcessor
from src.modelscope_manager import ModelScopeManager
from tools.simple_monitor import SimpleVideoMonitor


class SimpleVideoWorker:
    """简化的视频处理工作器"""
    
    def __init__(self):
        self.config = Config()
        self.logger = setup_logging('simple_worker')
        
        # 初始化组件
        self.video_processor = SimpleVideoProcessor(self.logger)
        # ModelScope管理器需要token参数
        self.modelscope_manager = ModelScopeManager(self.config.MODELSCOPE_TOKEN)
        self.monitor = SimpleVideoMonitor()
        
        # 工作目录
        self.temp_dir = tempfile.mkdtemp(prefix="simple_video_")
        self.logger.info(f"工作目录: {self.temp_dir}")
    
    def process_single_video(self, video_info: Dict) -> bool:
        """
        处理单个视频的完整流程
        
        Args:
            video_info: 视频信息字典
            
        Returns:
            bool: 处理是否成功
        """
        video_path = video_info["path"]
        self.logger.info(f"开始处理视频: {video_path}")
        
        local_input_path = None
        local_output_path = None
        
        try:
            # 步骤1: 下载视频文件
            self.logger.info(f"步骤1: 下载视频文件...")
            local_input_path = self._download_single_video(video_path)
            if not local_input_path:
                self.logger.error(f"下载失败: {video_path}")
                return False
            
            # 步骤2: 转换为MKV+AV1
            self.logger.info(f"步骤2: 转换视频格式...")
            local_output_path = self._convert_video(local_input_path)
            if not local_output_path:
                self.logger.error(f"转换失败: {video_path}")
                return False
            
            # 步骤3: 上传转换后的文件
            self.logger.info(f"步骤3: 上传转换后的文件...")
            output_repo_path = self._get_output_repo_path(video_path)
            if not self._upload_converted_video(local_output_path, output_repo_path):
                self.logger.error(f"上传失败: {video_path}")
                return False
            
            # 步骤4: 标记为已处理
            self.monitor.mark_video_processed(video_path)
            
            self.logger.info(f"视频处理完成: {video_path} → {output_repo_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"处理视频异常 {video_path}: {e}")
            return False
        
        finally:
            # 清理临时文件
            self._cleanup_temp_files(local_input_path, local_output_path)
    
    def _download_single_video(self, video_path: str) -> Optional[str]:
        """下载单个视频文件"""
        try:
            # 构造本地文件名
            filename = os.path.basename(video_path)
            local_path = os.path.join(self.temp_dir, f"input_{filename}")
            
            # 使用ModelScope CLI下载单个文件
            cmd = [
                "modelscope", "download",
                "--dataset", self.monitor.repo_id,
                "--include", video_path,
                "--cache_dir", self.temp_dir
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)  # 30分钟超时
            
            if result.returncode == 0:
                # 查找下载的文件
                for root, dirs, files in os.walk(self.temp_dir):
                    for file in files:
                        if file == filename or file.endswith(filename):
                            downloaded_path = os.path.join(root, file)
                            # 移动到标准位置
                            os.rename(downloaded_path, local_path)
                            self.logger.info(f"下载成功: {filename} ({os.path.getsize(local_path) // 1024 // 1024} MB)")
                            return local_path
                
                self.logger.error(f"下载后未找到文件: {filename}")
                return None
            else:
                self.logger.error(f"下载命令失败: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"下载超时: {video_path}")
            return None
        except Exception as e:
            self.logger.error(f"下载异常: {e}")
            return None
    
    def _convert_video(self, input_path: str) -> Optional[str]:
        """转换视频格式"""
        try:
            # 生成输出文件名 - 从原始文件名获取，不是从本地文件名
            original_filename = os.path.basename(input_path)
            # 去掉input_前缀
            if original_filename.startswith("input_"):
                original_filename = original_filename[6:]  # 去掉"input_"
            
            output_filename = self.video_processor.get_output_filename(original_filename)
            output_path = os.path.join(self.temp_dir, f"output_{output_filename}")
            
            # 执行转换
            if self.video_processor.convert_to_mkv_av1(input_path, output_path):
                return output_path
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"转换异常: {e}")
            return None
    
    def _get_output_repo_path(self, input_video_path: str) -> str:
        """生成输出文件的仓库路径"""
        # 保持目录结构，只改变文件扩展名
        directory = os.path.dirname(input_video_path)
        filename = os.path.basename(input_video_path)
        output_filename = self.video_processor.get_output_filename(filename)
        
        if directory:
            return f"{directory}/{output_filename}"
        else:
            return output_filename
    
    def _upload_converted_video(self, local_path: str, repo_path: str) -> bool:
        """上传转换后的视频"""
        try:
            # 使用正确的ModelScope CLI上传命令格式
            cmd = [
                "modelscope", "upload",
                self.monitor.repo_id,
                local_path,
                repo_path
            ]
            
            self.logger.info(f"上传命令: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
            
            if result.returncode == 0:
                file_size = os.path.getsize(local_path)
                self.logger.info(f"上传成功: {repo_path} ({file_size // 1024 // 1024} MB)")
                return True
            else:
                self.logger.error(f"上传失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"上传超时: {repo_path}")
            return False
        except Exception as e:
            self.logger.error(f"上传异常: {e}")
            return False
    
    def _cleanup_temp_files(self, *file_paths):
        """清理临时文件"""
        for file_path in file_paths:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    self.logger.debug(f"清理文件: {os.path.basename(file_path)}")
                except Exception as e:
                    self.logger.warning(f"清理失败 {file_path}: {e}")
    
    def run_worker(self):
        """运行工作器 - 持续处理队列中的视频"""
        self.logger.info("启动简化视频处理工作器...")
        
        try:
            while True:
                # 获取下一个要处理的视频
                next_video = self.monitor.get_next_video()
                
                if next_video:
                    # 处理视频
                    success = self.process_single_video(next_video)
                    
                    if success:
                        self.logger.info(f"✅ 处理成功: {next_video['path']}")
                    else:
                        self.logger.error(f"❌ 处理失败: {next_video['path']}")
                        # 失败的视频暂时跳过，避免死循环
                        self.monitor.mark_video_processed(next_video['path'])
                else:
                    # 队列为空，等待一段时间
                    self.logger.info("队列为空，等待新视频...")
                    time.sleep(30)
                
                # 显示队列状态
                status = self.monitor.get_queue_status()
                self.logger.info(f"队列状态: {status['queue_size']} 待处理, {status['processed_count']} 已完成")
                
        except KeyboardInterrupt:
            self.logger.info("工作器已停止")
        except Exception as e:
            self.logger.error(f"工作器异常: {e}")
        finally:
            # 清理工作目录
            try:
                import shutil
                shutil.rmtree(self.temp_dir)
                self.logger.info(f"清理工作目录: {self.temp_dir}")
            except:
                pass


def main():
    """主函数"""
    worker = SimpleVideoWorker()
    worker.run_worker()


if __name__ == "__main__":
    main() 