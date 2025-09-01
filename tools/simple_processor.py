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
        self.logger = setup_logging('video_worker')

        # 初始化组件
        self.video_processor = SimpleVideoProcessor(setup_logging('video_processor'))
        # ModelScope管理器需要token参数
        self.modelscope_manager = ModelScopeManager(self.config.MODELSCOPE_TOKEN)
        self.monitor = SimpleVideoMonitor()

        # 工作目录
        self.temp_dir = tempfile.mkdtemp(prefix="simple_video_")
        self.logger.info(f"工作目录: {self.temp_dir}")

        # 仓库配置
        self.input_repo_id = self.config.INPUT_REPO_ID   # 下载用
        self.output_repo_id = self.config.OUTPUT_REPO_ID  # 上传用
        
        # 确保ModelScope CLI已登录
        self._ensure_modelscope_login()
    
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
            
            # 使用正确的ModelScope CLI下载命令格式
            cmd = [
                "modelscope", "download",
                self.input_repo_id,             # repo_id (位置参数)
                self.temp_dir,                  # local_path (位置参数)  
                "--repo-type", "dataset",       # 指定为数据集仓库
                "--include", video_path,        # 只下载指定文件
                "--token", self.config.MODELSCOPE_TOKEN  # 明确指定token
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)  # 30分钟超时
            
            if result.returncode == 0:
                # 查找下载的文件
                for root, dirs, files in os.walk(self.temp_dir):
                    for file in files:
                        if file == filename or file.endswith(filename):
                            downloaded_path = os.path.join(root, file)
                            # 重命名为期望的文件名
                            final_path = os.path.join(self.temp_dir, f"input_{filename}")
                            if downloaded_path != final_path:
                                import shutil
                                shutil.move(downloaded_path, final_path)
                            
                            file_size = os.path.getsize(final_path)
                            self.logger.info(f"下载成功: {filename} ({file_size // 1024 // 1024} MB)")
                            return final_path
                
                self.logger.error(f"下载完成但未找到文件: {filename}")
                return None
            else:
                self.logger.error(f"下载失败: {result.stderr}")
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
            self.logger.info(f"准备上传文件:")
            self.logger.info(f"  本地路径: {local_path}")
            self.logger.info(f"  目标仓库: {self.output_repo_id}")
            self.logger.info(f"  目标路径: {repo_path}")
            
            # 检查本地文件
            if not os.path.exists(local_path):
                self.logger.error(f"本地文件不存在: {local_path}")
                return False
                
            file_size = os.path.getsize(local_path)
            self.logger.info(f"  文件大小: {file_size // 1024 // 1024} MB")
            
            # 方案1: 尝试CLI上传
            if self._upload_via_cli(local_path, repo_path, file_size):
                return True
            
            # 方案2: CLI失败时使用SDK上传
            self.logger.warning("🔄 CLI上传失败，尝试SDK上传...")
            return self._upload_via_sdk(local_path, repo_path, file_size)
                
        except Exception as e:
            self.logger.error(f"💥 上传流程异常: {e}")
            return False
    
    def _upload_via_cli(self, local_path: str, repo_path: str, file_size: int) -> bool:
        """通过CLI上传"""
        try:
            # 使用正确的ModelScope CLI上传命令格式 - 数据集上传
            cmd = [
                "modelscope", "upload",
                self.output_repo_id,        # repo_id (位置参数)
                local_path,                 # local_path (位置参数)
                repo_path,                  # path_in_repo (位置参数)
                "--repo-type", "dataset",   # 指定为数据集仓库
                "--commit-message", f"Upload converted video: {os.path.basename(repo_path)}",
                "--token", self.config.MODELSCOPE_TOKEN  # 明确指定token
            ]
            
            self.logger.info(f"🚀 CLI上传命令: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
            
            self.logger.info(f"命令返回码: {result.returncode}")
            if result.stdout:
                self.logger.info(f"命令输出: {result.stdout}")
            if result.stderr:
                self.logger.error(f"命令错误: {result.stderr}")
            
            if result.returncode == 0:
                self.logger.info(f"✅ CLI上传成功: {repo_path} ({file_size // 1024 // 1024} MB)")
                return True
            else:
                self.logger.error(f"❌ CLI上传失败，返回码: {result.returncode}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"⏰ CLI上传超时: {repo_path}")
            return False
        except Exception as e:
            self.logger.error(f"💥 CLI上传异常: {e}")
            return False
    
    def _upload_via_sdk(self, local_path: str, repo_path: str, file_size: int) -> bool:
        """通过SDK上传"""
        try:
            self.logger.info(f"🔧 SDK上传: {repo_path}")
            
            # 使用ModelScopeManager的API上传
            self.modelscope_manager.api.upload_file(
                path_or_fileobj=local_path,
                path_in_repo=repo_path,
                repo_id=self.output_repo_id,
                repo_type='dataset',
                commit_message=f'Upload converted video: {os.path.basename(repo_path)}',
                disable_tqdm=True
            )
            
            self.logger.info(f"✅ SDK上传成功: {repo_path} ({file_size // 1024 // 1024} MB)")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ SDK上传失败: {e}")
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
    
    def _ensure_modelscope_login(self):
        """确保ModelScope CLI已登录"""
        try:
            self.logger.info("检查ModelScope CLI登录状态...")
            # ModelScopeManager初始化时已经登录，这里通过CLI命令确认
            result = subprocess.run(
                ["modelscope", "login", "--token", self.config.MODELSCOPE_TOKEN],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                self.logger.info("✅ ModelScope CLI已登录")
            else:
                self.logger.warning(f"CLI登录警告: {result.stderr}")
                self.logger.info("继续使用SDK登录...")
        except Exception as e:
            self.logger.warning(f"CLI登录检查失败: {e}")
            self.logger.info("继续使用SDK登录...")
    
    def run_worker(self):
        """运行工作器 - 持续处理队列中的视频"""
        self.logger.info("启动视频处理工作器...")
        
        try:
            while True:
                # 获取下一个视频（会自动从队列中移除）
                next_video = self.monitor.get_next_video()
                
                if next_video:
                    video_path = next_video['path']
                    self.logger.info(f"🎬 开始处理: {video_path}")
                    
                    # 处理视频
                    success = self.process_single_video(next_video)
                    
                    if success:
                        self.logger.info(f"✅ 处理成功: {video_path}")
                        # process_single_video内部已经调用了mark_video_processed
                    else:
                        self.logger.error(f"❌ 处理失败: {video_path}")
                        # 标记为失败，避免重复处理
                        self.monitor.mark_video_failed(video_path)
                else:
                    # 队列为空，等待一段时间
                    self.logger.info("📪 队列为空，等待新视频...")
                    time.sleep(30)
                
                # 显示进度状态
                status = self.monitor.get_queue_status()
                self.logger.info(f"📊 进度: {status['processed_count']} 已完成, {status['queue_size']} 待处理")
                
        except KeyboardInterrupt:
            self.logger.info("🛑 工作器已停止")
        except Exception as e:
            self.logger.error(f"💥 工作器异常: {e}")
        finally:
            # 清理工作目录
            try:
                import shutil
                shutil.rmtree(self.temp_dir)
                self.logger.info(f"🧹 清理工作目录: {self.temp_dir}")
            except:
                pass


def main():
    """主函数"""
    worker = SimpleVideoWorker()
    worker.run_worker()


if __name__ == "__main__":
    main() 