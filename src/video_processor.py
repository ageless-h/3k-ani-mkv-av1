import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple, Optional
from scenedetect import VideoManager, SceneManager
from scenedetect.detectors import ContentDetector
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import Config
from src.utils import setup_logging, format_time, sanitize_filename

class VideoProcessor:
    def __init__(self, logger=None):
        self.logger = logger or setup_logging()
        self.config = Config()
    
    def convert_video_to_av1(self, input_path: str, output_path: str) -> bool:
        """将视频转换为AV1编码的MKV格式"""
        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 构建FFmpeg命令
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-y',  # 覆盖输出文件
                *self.config.FFMPEG_AV1_PARAMS,
                output_path
            ]
            
            self.logger.info(f"开始转换视频: {input_path}")
            self.logger.debug(f"FFmpeg命令: {' '.join(cmd)}")
            
            # 执行转换
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            if result.returncode == 0:
                self.logger.info(f"视频转换成功: {output_path}")
                return True
            else:
                self.logger.error(f"视频转换失败: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"视频转换出错: {str(e)}")
            return False
    
    def detect_scenes(self, video_path: str) -> List[Tuple[float, float]]:
        """检测视频中的场景切换点"""
        try:
            self.logger.info(f"开始检测场景: {video_path}")
            
            # 创建视频管理器
            video_manager = VideoManager([video_path])
            scene_manager = SceneManager()
            
            # 添加内容检测器
            scene_manager.add_detector(
                ContentDetector(threshold=self.config.SCENE_DETECTION_THRESHOLD)
            )
            
            # 开始检测
            video_manager.start()
            scene_manager.detect_scenes(frame_source=video_manager)
            
            # 获取场景列表
            scene_list = scene_manager.get_scene_list()
            
            # 转换为时间戳对
            scenes = []
            for scene in scene_list:
                start_time = scene[0].get_seconds()
                end_time = scene[1].get_seconds()
                scenes.append((start_time, end_time))
            
            self.logger.info(f"检测到 {len(scenes)} 个场景")
            return scenes
            
        except Exception as e:
            self.logger.error(f"场景检测出错: {str(e)}")
            return []
    
    def extract_middle_frame(self, video_path: str, start_time: float, 
                           end_time: float, output_path: str) -> bool:
        """提取场景中间帧"""
        try:
            # 计算中间时间点
            middle_time = (start_time + end_time) / 2
            
            # 构建FFmpeg命令
            cmd = [
                'ffmpeg',
                '-ss', str(middle_time),
                '-i', video_path,
                '-vframes', '1',
                '-q:v', '2',  # 高质量
                '-y',
                output_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            if result.returncode == 0 and os.path.exists(output_path):
                return True
            else:
                self.logger.warning(f"帧提取失败 at {format_time(middle_time)}: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"帧提取出错: {str(e)}")
            return False
    
    def extract_all_frames(self, video_path: str, output_dir: str) -> List[str]:
        """提取视频所有场景的中间帧"""
        try:
            self.logger.info(f"开始提取帧: {video_path}")
            
            # 检测场景
            scenes = self.detect_scenes(video_path)
            if not scenes:
                self.logger.warning(f"未检测到场景: {video_path}")
                return []
            
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            extracted_frames = []
            video_name = Path(video_path).stem
            
            for i, (start_time, end_time) in enumerate(scenes, 1):
                frame_filename = f"{sanitize_filename(video_name)}_scene_{i:04d}.jpg"
                frame_path = os.path.join(output_dir, frame_filename)
                
                if self.extract_middle_frame(video_path, start_time, end_time, frame_path):
                    extracted_frames.append(frame_path)
                    self.logger.debug(f"提取帧 {i}/{len(scenes)}: {format_time((start_time + end_time) / 2)}")
            
            self.logger.info(f"成功提取 {len(extracted_frames)} 帧，共 {len(scenes)} 个场景")
            return extracted_frames
            
        except Exception as e:
            self.logger.error(f"批量帧提取出错: {str(e)}")
            return []
    
    def get_video_info(self, video_path: str) -> Optional[dict]:
        """获取视频信息"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode == 0:
                import json
                return json.loads(result.stdout)
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"获取视频信息出错: {str(e)}")
            return None 