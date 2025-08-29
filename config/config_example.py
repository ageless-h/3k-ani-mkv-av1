import os
from pathlib import Path

class Config:
    # ==================== 路径配置 ====================
    # 源视频目录 - 包含待处理动画的根目录
    SOURCE_DIR = "/volume1/db/5_video/archive"
    
    # 图像输出目录 - tar包的最终存放位置
    OUTPUT_DIR = "/volume1/db/1_ai/data/image/animation"
    
    # 临时处理目录 - 用于存放处理过程中的临时文件
    TEMP_DIR = "/tmp/animation_processing"
    
    # 视频文件列表路径 - 预先准备的视频文件列表（可选）
    FILELIST_PATH = "/root/3k-animation-mkv-av1/code/filelist.txt"
    
    # 转换后视频存放目录（如果需要保存转换后的视频）
    VIDEO_OUTPUT_DIR = "/volume1/db/1_ai/data/video/animation"
    
    # ==================== 图像处理配置 ====================
    # 图像最大尺寸 - 图像长边不超过此值
    MAX_IMAGE_SIZE = 2048
    
    # 图像边长限制 - 超过此值的图像将被跳过
    MAX_EDGE_SIZE = 16383
    
    # WebP质量 - 0-100，90表示90%质量
    WEBP_QUALITY = 90
    
    # ==================== 批处理配置 ====================
    # 每批处理的最大集数 - 超过此数量将分批处理
    MAX_EPISODES_PER_BATCH = 30
    
    # 最小保留磁盘空间（GB）- 低于此值时停止处理
    MIN_FREE_SPACE_GB = 5
    
    # ==================== FFmpeg配置 ====================
    # AV1编码参数 - 用于视频转换
    FFMPEG_AV1_PARAMS = [
        "-c:v", "av1_nvenc",  # 使用NVIDIA硬件编码（如果支持）
        "-preset", "p7",      # 编码预设：p1(最快)到p7(最慢最高质量)
        "-crf", "23",         # 质量控制：0(无损)到63(最差)，推荐18-28
        "-c:a", "copy",       # 音频直接复制，不重新编码
        "-c:s", "copy",       # 字幕直接复制
        "-f", "matroska"      # 输出格式为MKV
    ]
    
    # 如果不支持硬件编码，可以改为：
    # FFMPEG_AV1_PARAMS = [
    #     "-c:v", "libaom-av1",  # 软件AV1编码
    #     "-cpu-used", "8",      # 编码速度：0(最慢)到8(最快)
    #     "-crf", "30",          # 软件编码建议稍高的CRF值
    #     "-c:a", "copy",
    #     "-c:s", "copy",
    #     "-f", "matroska"
    # ]
    
    # ==================== 场景检测配置 ====================
    # 场景检测阈值 - 值越小检测越敏感
    SCENE_DETECTION_THRESHOLD = 30.0
    
    # ==================== 性能配置 ====================
    # 最大并发工作线程数 - 根据CPU核心数和存储性能调整
    MAX_WORKERS = 2
    
    # ==================== 高级配置 ====================
    # libwebp路径配置 - 如果项目目录下有libwebp二进制文件
    LIBWEBP_PATH = "./libwebp/bin/cwebp"
    
    # 日志级别 - DEBUG, INFO, WARNING, ERROR
    LOG_LEVEL = "INFO"
    
    # 是否保留转换后的视频文件
    KEEP_CONVERTED_VIDEOS = False
    
    # 是否启用进度恢复功能
    ENABLE_RESUME = True
    
    @staticmethod
    def ensure_dirs():
        """确保必要的目录存在"""
        dirs_to_create = [
            Config.TEMP_DIR,
            Config.OUTPUT_DIR,
        ]
        
        # 如果需要保存转换后的视频，也创建视频输出目录
        if Config.KEEP_CONVERTED_VIDEOS:
            dirs_to_create.append(Config.VIDEO_OUTPUT_DIR)
        
        for dir_path in dirs_to_create:
            os.makedirs(dir_path, exist_ok=True)

# ==================== 配置验证 ====================
def validate_config():
    """验证配置是否正确"""
    config = Config()
    
    # 检查必要路径
    if not os.path.exists(config.SOURCE_DIR):
        print(f"警告: 源目录不存在: {config.SOURCE_DIR}")
    
    # 检查参数范围
    if not (0 <= config.WEBP_QUALITY <= 100):
        raise ValueError("WEBP_QUALITY 必须在 0-100 之间")
    
    if config.MAX_EPISODES_PER_BATCH <= 0:
        raise ValueError("MAX_EPISODES_PER_BATCH 必须大于 0")
    
    if config.MIN_FREE_SPACE_GB < 0:
        raise ValueError("MIN_FREE_SPACE_GB 不能为负数")
    
    print("✅ 配置验证通过")

# ==================== 使用说明 ====================
"""
使用方法：
1. 复制此文件为 config.py
2. 根据你的系统环境修改上述配置项
3. 运行 python check_environment.py 检查环境
4. 运行 python test_system.py 进行功能测试
5. 运行 python main.py 开始处理

重要配置项说明：
- SOURCE_DIR: 你的动画视频存放的根目录
- OUTPUT_DIR: 最终tar包的存放位置
- TEMP_DIR: 临时文件目录，需要足够的空间
- MAX_EPISODES_PER_BATCH: 如果某个动画系列集数很多，会自动分批处理

性能调优：
- 如果处理速度慢，可以增加 MAX_WORKERS
- 如果存储空间紧张，可以减少 MAX_EPISODES_PER_BATCH
- 如果对质量要求不高，可以降低 WEBP_QUALITY 和提高 CRF 值
""" 