import os
import subprocess
from pathlib import Path
from typing import List
from PIL import Image, ImageOps
from config import Config
from utils import setup_logging, sanitize_filename

class ImageProcessor:
    def __init__(self, logger=None):
        self.logger = logger or setup_logging()
        self.config = Config()
        
        # 根据记忆，用户希望直接调用项目文件夹中的libwebp二进制文件
        self.cwebp_path = "./libwebp/bin/cwebp"  # 假设libwebp在项目根目录下
    
    def resize_image(self, image_path: str, max_size: int = None) -> Image.Image:
        """调整图像大小，保持宽高比"""
        if max_size is None:
            max_size = self.config.MAX_IMAGE_SIZE
            
        try:
            with Image.open(image_path) as img:
                # 转换为RGB模式（如果不是的话）
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 获取原始尺寸
                width, height = img.size
                
                # 如果图像已经足够小，直接返回
                if max(width, height) <= max_size:
                    return img.copy()
                
                # 计算新尺寸，保持宽高比
                if width > height:
                    new_width = max_size
                    new_height = int(height * max_size / width)
                else:
                    new_height = max_size
                    new_width = int(width * max_size / height)
                
                # 使用双三次插值调整大小
                resized_img = img.resize((new_width, new_height), Image.BICUBIC)
                
                self.logger.debug(f"图像调整: {width}x{height} -> {new_width}x{new_height}")
                return resized_img
                
        except Exception as e:
            self.logger.error(f"图像调整失败 {image_path}: {str(e)}")
            raise
    
    def validate_image_size(self, img: Image.Image) -> bool:
        """验证图像尺寸是否符合要求"""
        width, height = img.size
        max_edge = max(width, height)
        
        if max_edge > self.config.MAX_EDGE_SIZE:
            self.logger.warning(f"图像边长超过限制: {max_edge} > {self.config.MAX_EDGE_SIZE}")
            return False
        
        return True
    
    def convert_to_webp_with_cwebp(self, input_path: str, output_path: str, quality: int = None) -> bool:
        """使用cwebp二进制文件转换图像为WebP格式"""
        if quality is None:
            quality = self.config.WEBP_QUALITY
            
        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 构建cwebp命令
            cmd = [
                self.cwebp_path,
                '-q', str(quality),
                input_path,
                '-o', output_path
            ]
            
            # 执行转换
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            if result.returncode == 0 and os.path.exists(output_path):
                self.logger.debug(f"WebP转换成功: {output_path}")
                return True
            else:
                self.logger.error(f"WebP转换失败: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"WebP转换出错: {str(e)}")
            return False
    
    def convert_to_webp_with_pillow(self, input_path: str, output_path: str, quality: int = None) -> bool:
        """使用Pillow转换图像为WebP格式（备用方案）"""
        if quality is None:
            quality = self.config.WEBP_QUALITY
            
        try:
            # 调整图像大小
            resized_img = self.resize_image(input_path)
            
            # 验证尺寸
            if not self.validate_image_size(resized_img):
                self.logger.warning(f"跳过尺寸不合格的图像: {input_path}")
                return False
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 保存为WebP格式
            resized_img.save(
                output_path,
                'WEBP',
                quality=quality,
                optimize=True
            )
            
            self.logger.debug(f"WebP转换成功: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"WebP转换出错: {str(e)}")
            return False
    
    def process_image(self, input_path: str, output_path: str, quality: int = None) -> bool:
        """处理单个图像（调整大小并转换为WebP）"""
        # 首先尝试使用cwebp
        if os.path.exists(self.cwebp_path):
            # 先用Pillow调整大小，然后用cwebp转换
            temp_path = output_path + ".temp.jpg"
            try:
                resized_img = self.resize_image(input_path)
                if not self.validate_image_size(resized_img):
                    return False
                
                # 保存临时JPEG文件
                resized_img.save(temp_path, 'JPEG', quality=95)
                
                # 使用cwebp转换
                success = self.convert_to_webp_with_cwebp(temp_path, output_path, quality)
                
                # 清理临时文件
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                
                return success
                
            except Exception as e:
                # 清理临时文件
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                self.logger.warning(f"cwebp处理失败，回退到Pillow: {str(e)}")
        
        # 回退到Pillow方案
        return self.convert_to_webp_with_pillow(input_path, output_path, quality)
    
    def rename_images_sequentially(self, image_list: List[str], output_dir: str, 
                                 start_number: int = 1) -> List[str]:
        """将图像重命名为连续的数字序列"""
        renamed_images = []
        
        for i, image_path in enumerate(image_list, start_number):
            # 生成新的文件名
            new_filename = f"{i:06d}.webp"
            new_path = os.path.join(output_dir, new_filename)
            
            try:
                # 移动并重命名文件
                if os.path.exists(image_path):
                    os.rename(image_path, new_path)
                    renamed_images.append(new_path)
                    self.logger.debug(f"重命名: {os.path.basename(image_path)} -> {new_filename}")
                
            except Exception as e:
                self.logger.error(f"重命名失败 {image_path}: {str(e)}")
        
        self.logger.info(f"重命名完成: {len(renamed_images)} 个文件")
        return renamed_images
    
    def batch_process_images(self, input_images: List[str], output_dir: str, 
                           start_number: int = 1) -> List[str]:
        """批量处理图像"""
        processed_images = []
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        for i, input_path in enumerate(input_images):
            try:
                # 生成临时输出路径
                temp_filename = f"temp_{i:06d}.webp"
                temp_path = os.path.join(output_dir, temp_filename)
                
                # 处理图像
                if self.process_image(input_path, temp_path):
                    processed_images.append(temp_path)
                else:
                    self.logger.warning(f"跳过处理失败的图像: {input_path}")
                    
            except Exception as e:
                self.logger.error(f"处理图像出错 {input_path}: {str(e)}")
        
        # 重命名为连续序列
        if processed_images:
            final_images = self.rename_images_sequentially(
                processed_images, output_dir, start_number
            )
            return final_images
        
        return [] 