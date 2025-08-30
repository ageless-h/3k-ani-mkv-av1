#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

class EnvironmentChecker:
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.info = []
        
    def log_issue(self, message):
        """记录严重问题"""
        self.issues.append(message)
        print(f"❌ 错误: {message}")
    
    def log_warning(self, message):
        """记录警告"""
        self.warnings.append(message)
        print(f"⚠️  警告: {message}")
    
    def log_info(self, message):
        """记录信息"""
        self.info.append(message)
        print(f"ℹ️  信息: {message}")
    
    def log_success(self, message):
        """记录成功"""
        print(f"✅ {message}")
    
    def check_python_version(self):
        """检查Python版本"""
        print("\n=== Python环境检查 ===")
        
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            self.log_issue(f"Python版本过低: {version.major}.{version.minor}, 需要 >= 3.8")
        else:
            self.log_success(f"Python版本: {version.major}.{version.minor}.{version.micro}")
    
    def check_system_info(self):
        """检查系统信息"""
        print("\n=== 系统信息 ===")
        
        self.log_info(f"操作系统: {platform.system()} {platform.release()}")
        self.log_info(f"架构: {platform.machine()}")
        self.log_info(f"处理器: {platform.processor()}")
        
        # 检查内存
        try:
            if platform.system() == "Linux":
                with open('/proc/meminfo', 'r') as f:
                    meminfo = f.read()
                    for line in meminfo.split('\n'):
                        if 'MemTotal:' in line:
                            mem_kb = int(line.split()[1])
                            mem_gb = mem_kb / 1024 / 1024
                            self.log_info(f"总内存: {mem_gb:.1f} GB")
                            
                            if mem_gb < 90:
                                self.log_warning(f"内存可能不足: {mem_gb:.1f} GB < 90 GB (推荐)")
                            else:
                                self.log_success(f"内存充足: {mem_gb:.1f} GB")
                            break
        except Exception as e:
            self.log_warning(f"无法获取内存信息: {str(e)}")
    
    def check_disk_space(self):
        """检查磁盘空间"""
        print("\n=== 磁盘空间检查 ===")
        
        # 检查根目录
        try:
            stat = shutil.disk_usage('/')
            free_gb = stat.free / (1024**3)
            total_gb = stat.total / (1024**3)
            
            self.log_info(f"根目录: {free_gb:.1f} GB 可用 / {total_gb:.1f} GB 总计")
            
            if free_gb < 50:
                self.log_warning(f"根目录空间不足: {free_gb:.1f} GB < 50 GB (推荐)")
            else:
                self.log_success(f"根目录空间充足: {free_gb:.1f} GB")
        
        except Exception as e:
            self.log_warning(f"无法检查磁盘空间: {str(e)}")
        
        # 检查临时目录
        try:
            stat = shutil.disk_usage('/tmp')
            free_gb = stat.free / (1024**3)
            
            self.log_info(f"临时目录 (/tmp): {free_gb:.1f} GB 可用")
            
            if free_gb < 50:
                self.log_warning(f"临时目录空间不足: {free_gb:.1f} GB < 50 GB (推荐)")
        
        except Exception as e:
            self.log_warning(f"无法检查临时目录空间: {str(e)}")
    
    def check_python_packages(self):
        """检查Python包"""
        print("\n=== Python包检查 ===")
        
        required_packages = [
            ('opencv-python', 'cv2'),
            ('scenedetect', 'scenedetect'),
            ('Pillow', 'PIL'),
            ('numpy', 'numpy'),
            ('tqdm', 'tqdm')
        ]
        
        for package_name, import_name in required_packages:
            try:
                __import__(import_name)
                self.log_success(f"{package_name} 已安装")
            except ImportError:
                self.log_issue(f"{package_name} 未安装 (pip install {package_name})")
    
    def check_ffmpeg(self):
        """检查FFmpeg"""
        print("\n=== FFmpeg检查 ===")
        
        # 检查FFmpeg是否安装
        if not shutil.which('ffmpeg'):
            self.log_issue("FFmpeg 未安装")
            return
        
        try:
            # 获取FFmpeg版本
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                self.log_success(f"FFmpeg: {version_line}")
            else:
                self.log_warning("FFmpeg 版本获取失败")
        
        except Exception as e:
            self.log_warning(f"FFmpeg 检查出错: {str(e)}")
        
        # 检查AV1硬件编码支持
        try:
            result = subprocess.run(['ffmpeg', '-encoders'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                if 'av1_nvenc' in result.stdout:
                    self.log_success("支持AV1硬件编码 (av1_nvenc)")
                else:
                    self.log_warning("不支持AV1硬件编码，将使用软件编码")
            
        except Exception as e:
            self.log_warning(f"编码器检查出错: {str(e)}")
        
        # 检查FFprobe
        if not shutil.which('ffprobe'):
            self.log_issue("FFprobe 未安装")
        else:
            self.log_success("FFprobe 已安装")
    
    def check_gpu(self):
        """检查GPU"""
        print("\n=== GPU检查 ===")
        
        # 检查nvidia-smi
        if not shutil.which('nvidia-smi'):
            self.log_warning("nvidia-smi 未找到，可能没有NVIDIA GPU")
            return
        
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,memory.free', 
                                   '--format=csv,noheader,nounits'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split(', ')
                        if len(parts) >= 3:
                            gpu_name = parts[0]
                            total_mem = int(parts[1])
                            free_mem = int(parts[2])
                            
                            self.log_success(f"GPU: {gpu_name}")
                            self.log_info(f"显存: {free_mem} MB 可用 / {total_mem} MB 总计")
                            
                            if total_mem < 16000:  # 小于16GB
                                self.log_warning(f"显存可能不足: {total_mem} MB < 16 GB (推荐)")
            else:
                self.log_warning("GPU信息获取失败")
        
        except Exception as e:
            self.log_warning(f"GPU检查出错: {str(e)}")
    
    def check_libwebp(self):
        """检查libwebp"""
        print("\n=== libwebp检查 ===")
        
        # 检查项目目录中的libwebp
        cwebp_paths = [
            "./libwebp/bin/cwebp",
            "./cwebp",
            "cwebp"
        ]
        
        cwebp_found = False
        for path in cwebp_paths:
            if os.path.exists(path) or shutil.which(path):
                try:
                    result = subprocess.run([path, '-version'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        self.log_success(f"libwebp 找到: {path}")
                        self.log_info(f"版本: {result.stdout.strip()}")
                        cwebp_found = True
                        break
                except Exception:
                    continue
        
        if not cwebp_found:
            self.log_warning("libwebp (cwebp) 未找到，将使用Pillow备用方案")
    
    def check_modelscope_setup(self):
        """检查魔搭社区配置"""
        print("\n=== 魔搭社区配置检查 ===")
        
        from config import Config
        config = Config()
        
        # 检查本地工作目录
        paths_to_check = [
            ("输出目录", config.OUTPUT_DIR),
            ("视频输出目录", config.VIDEO_OUTPUT_DIR),
            ("临时目录", config.TEMP_DIR),
            ("魔搭缓存目录", config.MODELSCOPE_CACHE_DIR),
            ("下载目录", config.DOWNLOAD_DIR),
            ("上传目录", config.UPLOAD_DIR)
        ]
        
        for name, path in paths_to_check:
            if os.path.exists(path):
                self.log_success(f"{name}: {path} (存在)")
            else:
                self.log_info(f"{name}: {path} (将自动创建)")
        
        # 检查魔搭Token
        if hasattr(config, 'MODELSCOPE_TOKEN') and config.MODELSCOPE_TOKEN:
            if config.MODELSCOPE_TOKEN.startswith('ms-'):
                self.log_success("魔搭Token配置正确")
            else:
                self.log_warning("魔搭Token格式可能不正确")
        else:
            self.log_warning("未配置魔搭Token")
        
        # 检查modelscope CLI
        try:
            result = subprocess.run(['modelscope', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.log_success("ModelScope CLI已安装")
            else:
                self.log_warning("ModelScope CLI未正确安装")
        except FileNotFoundError:
            self.log_warning("ModelScope CLI未安装")
        except Exception as e:
            self.log_warning(f"ModelScope CLI检查失败: {e}")
        
        # 检查是否有本地视频列表文件
        if os.path.exists("filelist.txt"):
            try:
                with open("filelist.txt", 'r', encoding='utf-8') as f:
                    videos = [line.strip() for line in f if line.strip()]
                    self.log_info(f"本地视频列表包含 {len(videos)} 个文件")
            except Exception as e:
                self.log_warning(f"读取本地视频列表失败: {str(e)}")
        else:
            self.log_info("未找到本地视频列表，将从魔搭仓库获取")
    
    def run_all_checks(self):
        """运行所有检查"""
        print("🔍 3K动画视频处理系统 - 环境检查")
        print("=" * 60)
        
        self.check_python_version()
        self.check_system_info()
        self.check_disk_space()
        self.check_python_packages()
        self.check_ffmpeg()
        self.check_gpu()
        self.check_libwebp()
        self.check_modelscope_setup()
        
        self.print_summary()
    
    def print_summary(self):
        """打印检查摘要"""
        print("\n" + "=" * 60)
        print("🏁 环境检查摘要")
        print("=" * 60)
        
        if self.issues:
            print(f"❌ 发现 {len(self.issues)} 个严重问题:")
            for issue in self.issues:
                print(f"   • {issue}")
            print()
        
        if self.warnings:
            print(f"⚠️  发现 {len(self.warnings)} 个警告:")
            for warning in self.warnings:
                print(f"   • {warning}")
            print()
        
        if not self.issues and not self.warnings:
            print("✅ 环境检查全部通过！系统已准备就绪。")
        elif not self.issues:
            print("✅ 没有严重问题，系统可以运行，但建议关注警告项。")
        else:
            print("❌ 发现严重问题，请解决后再运行系统。")
        
        print("\n💡 建议:")
        print("   • 如有严重问题，请先解决后再运行 python main.py")
        print("   • 如只有警告，可以尝试运行，但可能影响性能")
        print("   • 运行前建议先执行: python test_system.py")

def main():
    """主函数"""
    checker = EnvironmentChecker()
    
    try:
        checker.run_all_checks()
    except KeyboardInterrupt:
        print("\n\n用户中断检查")
    except Exception as e:
        print(f"\n\n检查过程出错: {str(e)}")

if __name__ == "__main__":
    main() 