#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
绿联云NAS专用配置
根据绿联云系统特点优化的配置参数
"""

import os
from pathlib import Path

class UgreenNASConfig:
    """绿联云NAS专用配置类"""
    
    # 绿联云常用的SSH用户名（按优先级排序）
    POSSIBLE_SSH_USERS = ["root", "admin", "ugos"]
    
    # 绿联云NAS信息
    NAS_IP = "100.74.107.59"
    NAS_NAME = "dh4300plus-0e7a"
    UGREEN_LINK_ID = "dh4300plus-0e7a-8NzJ"
    UGREEN_LINK_URL = "https://ug.link/dh4300plus-0e7a-8NzJ"
    
    # 可能的连接方式
    CONNECTION_METHODS = {
        "tailscale": "100.74.107.59",
        "ugreen_link": "ug.link/dh4300plus-0e7a-8NzJ",
        "local_lan": None  # 需要检测局域网IP
    }
    
    # 路径配置
    SOURCE_DIR = "/volume1/db/5_video/archive"
    OUTPUT_DIR = "/root/output/animation"
    TEMP_DIR = "/tmp/animation_processing"
    FILELIST_PATH = "/root/3k-ani-mkv-av1/filelist.txt"
    
    # 绿联云常见的共享目录路径
    POSSIBLE_VIDEO_PATHS = [
        "/volume1/db/5_video/archive",
        "/mnt/data/video",
        "/shares/video",
        "/volume1/video",
        "/data/video"
    ]
    
    # 网络配置
    SSH_PORT = 22
    CONNECTION_TIMEOUT = 30
    
    # 图像处理配置
    MAX_IMAGE_SIZE = 2048
    WEBP_QUALITY = 90
    MAX_EPISODES_PER_BATCH = 30
    
    # FFmpeg配置（针对绿联云硬件优化）
    FFMPEG_AV1_PARAMS = [
        "-c:v", "av1_nvenc",
        "-preset", "p6",      # 绿联云建议使用p6平衡性能和质量
        "-crf", "23",
        "-c:a", "copy",
        "-c:s", "copy", 
        "-f", "matroska"
    ]

def detect_best_connection():
    """检测最佳的连接方式"""
    import subprocess
    import socket
    
    print("🔍 检测最佳连接方式...")
    
    # 1. 测试Tailscale连接
    print("\n1. 测试Tailscale连接 (100.74.107.59)")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex(("100.74.107.59", 22))
        sock.close()
        
        if result == 0:
            print("✅ Tailscale SSH端口可达")
            return "tailscale", "100.74.107.59"
        else:
            print(f"❌ Tailscale SSH端口不可达 (错误{result})")
    except Exception as e:
        print(f"❌ Tailscale连接测试失败: {str(e)}")
    
    # 2. 尝试检测局域网IP
    print("\n2. 尝试检测局域网连接")
    # 常见的绿联云局域网IP段
    common_ips = [
        "192.168.1.100", "192.168.1.200", "192.168.1.10",
        "192.168.0.100", "192.168.0.200", "192.168.0.10",
        "10.0.0.100", "10.0.0.200"
    ]
    
    for ip in common_ips:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((ip, 22))
            sock.close()
            
            if result == 0:
                print(f"✅ 发现局域网NAS: {ip}")
                return "local_lan", ip
        except:
            pass
    
    print("❌ 未找到局域网连接")
    
    # 3. UGREENlink连接（需要特殊处理）
    print("\n3. UGREENlink远程连接")
    print("⚠️  UGREENlink需要通过Web界面或专用客户端访问")
    print(f"   Web地址: {UgreenNASConfig.UGREEN_LINK_URL}")
    
    return None, None

def detect_ssh_user(nas_ip="100.74.107.59"):
    """自动检测可用的SSH用户名"""
    import subprocess
    
    print(f"\n🔑 检测SSH用户名 ({nas_ip})")
    
    for user in UgreenNASConfig.POSSIBLE_SSH_USERS:
        try:
            # 测试SSH连接
            result = subprocess.run([
                'ssh', '-o', 'ConnectTimeout=5', '-o', 'BatchMode=yes',
                '-o', 'StrictHostKeyChecking=no', f'{user}@{nas_ip}', 
                'echo test'
            ], capture_output=True, timeout=10)
            
            if result.returncode == 0:
                print(f"✅ 检测到可用SSH用户: {user}")
                return user
            elif result.returncode == 255:
                # SSH连接成功但认证失败，说明用户名是对的
                print(f"⚠️  用户 {user} 存在但需要密码认证")
                return user
            else:
                print(f"❌ 用户 {user} - 连接失败")
                
        except Exception as e:
            print(f"❌ 测试用户 {user} 失败: {str(e)}")
    
    print("❌ 未找到可用的SSH用户")
    return None

def test_video_paths(ssh_user, nas_ip="100.74.107.59"):
    """测试视频目录路径是否存在"""
    import subprocess
    
    available_paths = []
    
    for path in UgreenNASConfig.POSSIBLE_VIDEO_PATHS:
        try:
            result = subprocess.run([
                'ssh', '-o', 'ConnectTimeout=5', '-o', 'StrictHostKeyChecking=no',
                f'{ssh_user}@{nas_ip}', f'test -d "{path}" && echo "exists"'
            ], capture_output=True, timeout=10, text=True)
            
            if result.returncode == 0 and "exists" in result.stdout:
                available_paths.append(path)
                print(f"✅ 视频目录存在: {path}")
            else:
                print(f"❌ 视频目录不存在: {path}")
                
        except Exception as e:
            print(f"测试路径 {path} 失败: {str(e)}")
    
    return available_paths

def generate_ugreen_config(ssh_user, video_path=None):
    """生成适合绿联云的配置文件"""
    
    config_content = f'''import os
from pathlib import Path

class Config:
    # 绿联云NAS配置
    NAS_IP = "{UgreenNASConfig.NAS_IP}"
    SSH_USER = "{ssh_user}"
    SSH_PORT = {UgreenNASConfig.SSH_PORT}
    
    # 路径配置
    SOURCE_DIR = "{video_path or UgreenNASConfig.SOURCE_DIR}"
    OUTPUT_DIR = "{UgreenNASConfig.OUTPUT_DIR}"
    TEMP_DIR = "{UgreenNASConfig.TEMP_DIR}"
    FILELIST_PATH = "{UgreenNASConfig.FILELIST_PATH}"
    VIDEO_OUTPUT_DIR = "/root/output/video"
    
    # 图像处理配置
    MAX_IMAGE_SIZE = {UgreenNASConfig.MAX_IMAGE_SIZE}
    MAX_EDGE_SIZE = 16383
    WEBP_QUALITY = {UgreenNASConfig.WEBP_QUALITY}
    
    # 批处理配置
    MAX_EPISODES_PER_BATCH = {UgreenNASConfig.MAX_EPISODES_PER_BATCH}
    MIN_FREE_SPACE_GB = 5
    
    # FFmpeg配置（绿联云优化）
    FFMPEG_AV1_PARAMS = {UgreenNASConfig.FFMPEG_AV1_PARAMS}
    
    # 场景检测配置
    SCENE_DETECTION_THRESHOLD = 30.0
    
    # 性能配置
    MAX_WORKERS = 3  # 绿联云推荐值
    
    @staticmethod
    def ensure_dirs():
        """确保必要的目录存在"""
        dirs_to_create = [
            Config.TEMP_DIR,
            Config.OUTPUT_DIR,
            Config.VIDEO_OUTPUT_DIR
        ]
        for dir_path in dirs_to_create:
            try:
                os.makedirs(dir_path, exist_ok=True)
            except:
                pass
'''
    
    return config_content

if __name__ == "__main__":
    print("🔍 绿联云NAS配置检测")
    print("=" * 50)
    print(f"设备信息: {UgreenNASConfig.NAS_NAME}")
    print(f"UGREENlink ID: {UgreenNASConfig.UGREEN_LINK_ID}")
    print(f"远程访问: {UgreenNASConfig.UGREEN_LINK_URL}")
    print("=" * 50)
    
    # 检测最佳连接方式
    connection_type, nas_ip = detect_best_connection()
    
    if connection_type and nas_ip:
        print(f"\n✅ 最佳连接方式: {connection_type} ({nas_ip})")
        
        # 检测SSH用户
        ssh_user = detect_ssh_user(nas_ip)
        
        if ssh_user:
            print(f"\n📂 检测视频目录...")
            video_paths = test_video_paths(ssh_user, nas_ip)
            
            if video_paths:
                print(f"\n✅ 推荐配置:")
                print(f"   连接方式: {connection_type}")
                print(f"   NAS地址: {nas_ip}")
                print(f"   SSH用户: {ssh_user}")
                print(f"   视频目录: {video_paths[0]}")
                
                # 生成配置文件
                config_content = generate_ugreen_config(ssh_user, video_paths[0])
                config_content = config_content.replace(
                    f'NAS_IP = "{UgreenNASConfig.NAS_IP}"',
                    f'NAS_IP = "{nas_ip}"  # {connection_type} connection'
                )
                
                print(f"\n📝 生成的config.py内容:")
                print("-" * 50)
                print(config_content)
                
                # 保存配置到文件
                try:
                    with open("config_generated.py", "w", encoding="utf-8") as f:
                        f.write(config_content)
                    print(f"\n💾 配置已保存到: config_generated.py")
                    print("   使用方法: cp config_generated.py config.py")
                except Exception as e:
                    print(f"\n❌ 保存配置失败: {str(e)}")
                
            else:
                print("\n⚠️  未找到标准视频目录，请手动确认路径")
        else:
            print("\n❌ SSH用户检测失败，可能需要:")
            print("   1. 在绿联云Web界面启用SSH服务")
            print("   2. 设置SSH用户权限")
            print("   3. 检查防火墙设置")
    else:
        print("\n❌ 无法建立网络连接，请检查:")
        print("   1. Tailscale连接状态")
        print("   2. 局域网连接")
        print("   3. 绿联云SSH服务是否启用")
        print(f"   4. 也可尝试通过UGREENlink访问: {UgreenNASConfig.UGREEN_LINK_URL}") 