import os
import tarfile
import shutil
from pathlib import Path
from typing import List, Dict
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import Config
from src.utils import setup_logging, check_free_space, sanitize_filename, get_disk_usage

class ArchiveManager:
    def __init__(self, logger=None):
        self.logger = logger or setup_logging()
        self.config = Config()
    
    def create_tar_archive(self, source_dir: str, archive_path: str, 
                          compression: str = 'gz') -> bool:
        """创建tar压缩包"""
        try:
            self.logger.info(f"开始创建归档: {archive_path}")
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(archive_path), exist_ok=True)
            
            # 获取压缩模式
            mode = f'w:{compression}' if compression else 'w'
            
            # 创建tar文件
            with tarfile.open(archive_path, mode) as tar:
                # 遍历源目录中的所有文件
                for root, dirs, files in os.walk(source_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # 计算在tar包中的相对路径
                        arcname = os.path.relpath(file_path, source_dir)
                        tar.add(file_path, arcname=arcname)
                        self.logger.debug(f"添加到归档: {arcname}")
            
            # 验证归档文件是否创建成功
            if os.path.exists(archive_path):
                archive_size = os.path.getsize(archive_path) / (1024**2)  # MB
                self.logger.info(f"归档创建成功: {archive_path} ({archive_size:.2f} MB)")
                return True
            else:
                self.logger.error(f"归档创建失败: {archive_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"创建归档出错: {str(e)}")
            return False
    
    def estimate_archive_size(self, source_dir: str) -> float:
        """估算归档文件大小（MB）"""
        try:
            total_size = 0
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)
            
            # 估算压缩后大小（WebP文件压缩率较低，约80%）
            estimated_compressed_size = total_size * 0.8
            return estimated_compressed_size / (1024**2)  # 转换为MB
            
        except Exception as e:
            self.logger.error(f"估算归档大小出错: {str(e)}")
            return 0
    
    def check_space_before_archive(self, source_dir: str, target_dir: str) -> bool:
        """检查创建归档前是否有足够空间"""
        try:
            estimated_size_mb = self.estimate_archive_size(source_dir)
            required_space_gb = (estimated_size_mb / 1024) + self.config.MIN_FREE_SPACE_GB
            
            if check_free_space(target_dir, required_space_gb):
                self.logger.info(f"空间检查通过: 需要 {required_space_gb:.2f} GB")
                return True
            else:
                disk_info = get_disk_usage(target_dir)
                self.logger.warning(f"空间不足: 需要 {required_space_gb:.2f} GB, 可用 {disk_info['free']:.2f} GB")
                return False
                
        except Exception as e:
            self.logger.error(f"空间检查出错: {str(e)}")
            return False
    
    def cleanup_temp_files(self, temp_dir: str):
        """清理临时文件"""
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                self.logger.info(f"清理临时目录: {temp_dir}")
            else:
                self.logger.debug(f"临时目录不存在: {temp_dir}")
                
        except Exception as e:
            self.logger.error(f"清理临时文件出错: {str(e)}")
    
    def move_archive_to_destination(self, archive_path: str, destination: str) -> bool:
        """将归档文件移动到最终目标位置"""
        try:
            # 确保目标目录存在
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            
            # 移动文件
            shutil.move(archive_path, destination)
            self.logger.info(f"归档移动完成: {destination}")
            return True
            
        except Exception as e:
            self.logger.error(f"移动归档文件出错: {str(e)}")
            return False
    
    def generate_archive_name(self, series_name: str, batch_info: Dict = None) -> str:
        """生成归档文件名"""
        # 清理系列名称
        clean_name = sanitize_filename(series_name)
        
        if batch_info and batch_info.get('is_multi_batch', False):
            # 多批次模式
            batch_num = batch_info.get('batch_number', 1)
            total_batches = batch_info.get('total_batches', 1)
            archive_name = f"{clean_name}_part{batch_num:02d}of{total_batches:02d}.tar.gz"
        else:
            # 单批次模式
            archive_name = f"{clean_name}.tar.gz"
        
        return archive_name
    
    def create_series_archive(self, series_name: str, images_dir: str, 
                            batch_info: Dict = None) -> str:
        """为单个系列创建归档"""
        try:
            # 生成归档文件名
            archive_name = self.generate_archive_name(series_name, batch_info)
            temp_archive_path = os.path.join(self.config.TEMP_DIR, archive_name)
            final_archive_path = os.path.join(self.config.OUTPUT_DIR, archive_name)
            
            # 检查空间
            if not self.check_space_before_archive(images_dir, self.config.TEMP_DIR):
                raise Exception("磁盘空间不足")
            
            # 创建归档
            if self.create_tar_archive(images_dir, temp_archive_path):
                # 移动到最终位置
                if self.move_archive_to_destination(temp_archive_path, final_archive_path):
                    return final_archive_path
                else:
                    raise Exception("归档移动失败")
            else:
                raise Exception("归档创建失败")
                
        except Exception as e:
            self.logger.error(f"系列归档失败 {series_name}: {str(e)}")
            return None
    
    def verify_archive(self, archive_path: str) -> bool:
        """验证归档文件完整性"""
        try:
            with tarfile.open(archive_path, 'r') as tar:
                # 尝试列出所有文件
                members = tar.getmembers()
                self.logger.info(f"归档验证成功: {len(members)} 个文件")
                return True
                
        except Exception as e:
            self.logger.error(f"归档验证失败 {archive_path}: {str(e)}")
            return False
    
    def get_archive_info(self, archive_path: str) -> Dict:
        """获取归档文件信息"""
        try:
            info = {
                'path': archive_path,
                'exists': os.path.exists(archive_path),
                'size_mb': 0,
                'file_count': 0
            }
            
            if info['exists']:
                info['size_mb'] = os.path.getsize(archive_path) / (1024**2)
                
                # 计算文件数量
                with tarfile.open(archive_path, 'r') as tar:
                    info['file_count'] = len(tar.getmembers())
            
            return info
            
        except Exception as e:
            self.logger.error(f"获取归档信息出错: {str(e)}")
            return {'path': archive_path, 'exists': False, 'size_mb': 0, 'file_count': 0} 