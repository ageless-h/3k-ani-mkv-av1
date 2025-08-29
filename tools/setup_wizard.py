#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置向导工具
帮助用户交互式配置3K动画处理系统
"""

import os
import sys
import json
import socket
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SetupWizard:
    """配置向导"""
    
    def __init__(self):
        self.config_data = {}
        self.project_root = Path(__file__).parent.parent
        
    def welcome(self):
        """欢迎界面"""
        print("🎬 3K动画视频处理系统 - 配置向导")
        print("=" * 60)
        print("本向导将帮助您配置项目环境")
        print("请按照提示输入相关信息，按回车使用默认值")
        print("=" * 60)
        print()
    
    def detect_current_environment(self) -> Dict[str, str]:
        """检测当前环境"""
        print("🔍 检测当前环境...")
        
        env_info = {
            'os': sys.platform,
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            'current_dir': str(Path.cwd()),
            'user': os.getenv('USER', os.getenv('USERNAME', 'unknown'))
        }
        
        # 检测是否在Tailscale网络中
        try:
            result = subprocess.run(['tailscale', 'status'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                env_info['tailscale'] = 'available'
                # 解析Tailscale设备
                devices = {}
                for line in result.stdout.split('\n'):
                    if line.strip() and not line.startswith('#'):
                        parts = line.split()
                        if len(parts) >= 2:
                            ip = parts[0]
                            name = parts[1]
                            devices[name] = ip
                env_info['tailscale_devices'] = devices
            else:
                env_info['tailscale'] = 'not_available'
        except:
            env_info['tailscale'] = 'not_available'
        
        print(f"  操作系统: {env_info['os']}")
        print(f"  Python版本: {env_info['python_version']}")
        print(f"  当前用户: {env_info['user']}")
        print(f"  Tailscale: {env_info['tailscale']}")
        
        if env_info.get('tailscale_devices'):
            print("  Tailscale设备:")
            for name, ip in env_info['tailscale_devices'].items():
                print(f"    {name}: {ip}")
        
        print()
        return env_info
    
    def configure_deployment_mode(self) -> str:
        """配置部署模式"""
        print("📋 选择部署模式:")
        print("1. 单机模式 (本地处理)")
        print("2. 远程模式 (Linux服务器处理)")
        print("3. 中介模式 (通过中介机传输)")
        
        while True:
            choice = input("请选择部署模式 (1-3) [2]: ").strip()
            if not choice:
                choice = "2"
            
            if choice in ["1", "2", "3"]:
                modes = {"1": "local", "2": "remote", "3": "bridge"}
                mode = modes[choice]
                print(f"✅ 选择部署模式: {mode}")
                return mode
            else:
                print("❌ 无效选择，请输入1、2或3")
    
    def configure_nas_connection(self, env_info: Dict) -> Dict[str, str]:
        """配置NAS连接"""
        print("\n🔧 配置NAS连接:")
        
        nas_config = {}
        
        # 如果检测到Tailscale设备，提供选择
        if env_info.get('tailscale_devices'):
            print("检测到以下Tailscale设备:")
            devices = list(env_info['tailscale_devices'].items())
            for i, (name, ip) in enumerate(devices, 1):
                print(f"  {i}. {name} ({ip})")
            
            choice = input(f"选择NAS设备 (1-{len(devices)}) 或手动输入IP: ").strip()
            
            if choice.isdigit() and 1 <= int(choice) <= len(devices):
                name, ip = devices[int(choice) - 1]
                nas_config['nas_ip'] = ip
                nas_config['nas_name'] = name
                print(f"✅ 选择NAS: {name} ({ip})")
            else:
                nas_config['nas_ip'] = choice if choice else "100.74.107.59"
                nas_config['nas_name'] = input("NAS名称 [dh4300plus-0e7a]: ").strip() or "dh4300plus-0e7a"
        else:
            nas_config['nas_ip'] = input("NAS IP地址 [100.74.107.59]: ").strip() or "100.74.107.59"
            nas_config['nas_name'] = input("NAS名称 [dh4300plus-0e7a]: ").strip() or "dh4300plus-0e7a"
        
        nas_config['ssh_user'] = input("SSH用户名 [root]: ").strip() or "root"
        nas_config['ssh_port'] = input("SSH端口 [22]: ").strip() or "22"
        
        # 测试连接
        if self._test_nas_connection(nas_config['nas_ip'], int(nas_config['ssh_port'])):
            print("✅ NAS连接测试成功")
        else:
            print("⚠️  NAS连接测试失败，请检查配置")
        
        return nas_config
    
    def configure_paths(self, mode: str) -> Dict[str, str]:
        """配置路径"""
        print("\n📁 配置路径:")
        
        paths = {}
        
        # NAS路径
        paths['nas_source'] = input("NAS源视频目录 [/volume1/db/5_video/archive]: ").strip() or "/volume1/db/5_video/archive"
        paths['nas_output'] = input("NAS输出目录 [/volume1/db/1_ai/data/image/animation]: ").strip() or "/volume1/db/1_ai/data/image/animation"
        
        # 本地/远程路径
        if mode == "local":
            paths['local_temp'] = input("本地临时目录 [/tmp/animation_processing]: ").strip() or "/tmp/animation_processing"
            paths['local_output'] = input("本地输出目录 [./output]: ").strip() or "./output"
        elif mode == "remote":
            paths['remote_temp'] = input("远程临时目录 [/tmp/animation_processing]: ").strip() or "/tmp/animation_processing"
            paths['remote_output'] = input("远程输出目录 [/root/output]: ").strip() or "/root/output"
            paths['remote_project'] = input("远程项目目录 [/root/3k-ani-mkv-av1]: ").strip() or "/root/3k-ani-mkv-av1"
        elif mode == "bridge":
            paths['waas_temp'] = input("waas临时目录 [/tmp/animation_processing]: ").strip() or "/tmp/animation_processing"
            paths['waas_output'] = input("waas输出目录 [/root/output]: ").strip() or "/root/output"
            paths['waas_project'] = input("waas项目目录 [/root/3k-ani-mkv-av1]: ").strip() or "/root/3k-ani-mkv-av1"
        
        return paths
    
    def configure_processing_settings(self) -> Dict[str, any]:
        """配置处理设置"""
        print("\n⚙️  配置处理设置:")
        
        settings = {}
        
        # 视频处理设置
        settings['max_episodes_per_batch'] = int(input("每批最大集数 [30]: ").strip() or "30")
        settings['max_workers'] = int(input("最大并发工作线程 [4]: ").strip() or "4")
        
        # 图像设置
        settings['webp_quality'] = int(input("WebP质量 (1-100) [90]: ").strip() or "90")
        settings['target_size'] = int(input("图像目标尺寸 [2048]: ").strip() or "2048")
        settings['max_image_size'] = int(input("最大图像尺寸 [16383]: ").strip() or "16383")
        
        # 硬件设置
        use_gpu = input("使用GPU硬件加速? (y/n) [y]: ").strip().lower()
        settings['use_gpu_encoding'] = use_gpu != 'n'
        
        if settings['use_gpu_encoding']:
            settings['gpu_encoder'] = input("GPU编码器 [av1_nvenc]: ").strip() or "av1_nvenc"
        
        # 存储设置
        settings['keep_converted_videos'] = input("保留转换后的视频? (y/n) [n]: ").strip().lower() == 'y'
        settings['min_free_space_gb'] = int(input("最小剩余空间 (GB) [10]: ").strip() or "10")
        
        return settings
    
    def configure_bridge_mode(self, env_info: Dict) -> Dict[str, str]:
        """配置中介模式"""
        if env_info.get('tailscale_devices'):
            print("\n🌉 配置中介传输:")
            
            bridge_config = {}
            devices = list(env_info['tailscale_devices'].items())
            
            print("检测到以下设备:")
            for i, (name, ip) in enumerate(devices, 1):
                print(f"  {i}. {name} ({ip})")
            
            # 选择waas服务器
            choice = input("选择waas处理服务器: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(devices):
                name, ip = devices[int(choice) - 1]
                bridge_config['waas_ip'] = ip
                bridge_config['waas_name'] = name
            
            # 选择中介机 (当前机器)
            current_name = None
            for name, ip in devices:
                if self._is_current_machine(ip):
                    current_name = name
                    bridge_config['bridge_ip'] = ip
                    bridge_config['bridge_name'] = name
                    break
            
            if current_name:
                print(f"✅ 检测到当前机器: {current_name}")
            else:
                print("⚠️  未检测到当前机器，请手动配置")
            
            return bridge_config
        
        return {}
    
    def generate_config_files(self, mode: str, nas_config: Dict, paths: Dict, 
                            settings: Dict, bridge_config: Dict = None):
        """生成配置文件"""
        print("\n📝 生成配置文件...")
        
        # 生成主配置文件
        self._generate_main_config(mode, nas_config, paths, settings)
        
        # 如果是中介模式，生成中介配置
        if mode == "bridge" and bridge_config:
            self._generate_bridge_config(nas_config, bridge_config, paths)
        
        # 生成启动脚本
        self._generate_run_script(mode)
        
        print("✅ 配置文件生成完成")
    
    def _generate_main_config(self, mode: str, nas_config: Dict, paths: Dict, settings: Dict):
        """生成主配置文件"""
        config_content = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
3K动画视频处理系统配置文件
由配置向导自动生成于 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

class Config:
    # === 部署模式 ===
    DEPLOYMENT_MODE = "{mode}"  # local, remote, bridge
    
    # === NAS连接配置 ===
    NAS_IP = "{nas_config['nas_ip']}"
    NAS_NAME = "{nas_config['nas_name']}"
    SSH_USER = "{nas_config['ssh_user']}"
    SSH_PORT = {nas_config['ssh_port']}
    
    # === 路径配置 ===
    SOURCE_DIR = "{paths['nas_source']}"
    NAS_OUTPUT_DIR = "{paths['nas_output']}"
    '''
        
        if mode == "local":
            config_content += f'''
    TEMP_DIR = "{paths['local_temp']}"
    OUTPUT_DIR = "{paths['local_output']}"
    '''
        elif mode == "remote":
            config_content += f'''
    TEMP_DIR = "{paths['remote_temp']}"
    OUTPUT_DIR = "{paths['remote_output']}"
    PROJECT_DIR = "{paths['remote_project']}"
    '''
        elif mode == "bridge":
            config_content += f'''
    TEMP_DIR = "{paths['waas_temp']}"
    OUTPUT_DIR = "{paths['waas_output']}"
    PROJECT_DIR = "{paths['waas_project']}"
    '''
        
        config_content += f'''
    # === 处理参数 ===
    MAX_EPISODES_PER_BATCH = {settings['max_episodes_per_batch']}
    MAX_WORKERS = {settings['max_workers']}
    
    # === 图像设置 ===
    WEBP_QUALITY = {settings['webp_quality']}
    TARGET_SIZE = {settings['target_size']}
    MAX_IMAGE_SIZE = {settings['max_image_size']}
    
    # === 硬件设置 ===
    USE_GPU_ENCODING = {settings['use_gpu_encoding']}'''
        
        if settings['use_gpu_encoding']:
            config_content += f'''
    GPU_ENCODER = "{settings['gpu_encoder']}"'''
        
        config_content += f'''
    
    # === 存储设置 ===
    KEEP_CONVERTED_VIDEOS = {settings['keep_converted_videos']}
    MIN_FREE_SPACE_GB = {settings['min_free_space_gb']}
    
    # === 文件列表 ===
    FILELIST_PATH = "filelist.txt"
'''
        
        # 保存配置文件
        config_path = self.project_root / "config" / "config.py"
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        print(f"  ✅ 主配置文件: {config_path}")
    
    def _generate_bridge_config(self, nas_config: Dict, bridge_config: Dict, paths: Dict):
        """生成中介配置文件"""
        from datetime import datetime
        
        bridge_content = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
中介传输配置文件
由配置向导自动生成于 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

class BridgeConfig:
    # === 网络拓扑配置 ===
    NAS_IP = "{nas_config['nas_ip']}"
    NAS_NAME = "{nas_config['nas_name']}"
    NAS_SSH_USER = "{nas_config['ssh_user']}"
    NAS_SSH_PORT = {nas_config['ssh_port']}
    
    WAAS_IP = "{bridge_config.get('waas_ip', '100.95.10.55')}"
    WAAS_NAME = "{bridge_config.get('waas_name', 'waas')}"
    WAAS_SSH_USER = "root"
    WAAS_SSH_PORT = 22
    
    BRIDGE_IP = "{bridge_config.get('bridge_ip', '100.69.148.34')}"
    BRIDGE_NAME = "{bridge_config.get('bridge_name', 'win-fjcmcrnsif0')}"
    
    # === 路径配置 ===
    NAS_SOURCE_DIR = "{paths['nas_source']}"
    NAS_OUTPUT_DIR = "{paths['nas_output']}"
    
    WAAS_TEMP_DIR = "{paths['waas_temp']}"
    WAAS_OUTPUT_DIR = "{paths['waas_output']}"
    WAAS_PROJECT_DIR = "{paths['waas_project']}"
    
    # === 传输配置 ===
    TRANSFER_METHODS = ["rsync", "scp", "sftp"]
    MAX_CONCURRENT_TRANSFERS = 2
    TRANSFER_TIMEOUT = 300
    RETRY_COUNT = 3
    
    # === SSH配置 ===
    SSH_OPTIONS = [
        "-o ConnectTimeout=30",
        "-o ServerAliveInterval=60",
        "-o ServerAliveCountMax=3",
        "-o StrictHostKeyChecking=no",
        "-o UserKnownHostsFile=/dev/null"
    ]
'''
        
        # 保存中介配置文件
        bridge_path = self.project_root / "config" / "bridge_config.py"
        with open(bridge_path, 'w', encoding='utf-8') as f:
            f.write(bridge_content)
        
        print(f"  ✅ 中介配置文件: {bridge_path}")
    
    def _generate_run_script(self, mode: str):
        """生成启动脚本"""
        if mode == "bridge":
            script_content = '''#!/bin/bash

# 3K动画处理系统 - 中介模式启动脚本

echo "🌉 3K动画处理系统 - 中介模式"
echo "=================================="

# 检查配置
if [ ! -f "config/config.py" ] || [ ! -f "config/bridge_config.py" ]; then
    echo "❌ 配置文件缺失，请运行配置向导: python3 tools/setup_wizard.py"
    exit 1
fi

# 启动中介传输工具
echo "启动中介传输工具..."
python3 tools/bridge_transfer.py

echo "=================================="
echo "中介传输完成！"
'''
        else:
            script_content = '''#!/bin/bash

# 3K动画处理系统启动脚本

echo "🎬 3K动画视频处理系统"
echo "=================================="

# 检查配置
if [ ! -f "config/config.py" ]; then
    echo "❌ 配置文件不存在，请运行配置向导: python3 tools/setup_wizard.py"
    exit 1
fi

# 检查环境
echo "检查系统环境..."
python3 tools/check_environment.py

# 创建日志目录
mkdir -p log

# 启动主程序
echo "启动主程序..."
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

python3 -c "
import sys
sys.path.insert(0, '.')
from src.main import main
main()
"

echo "=================================="
echo "处理完成！"
'''
        
        run_script_path = self.project_root / "run.sh"
        with open(run_script_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(script_content)
        
        print(f"  ✅ 启动脚本: {run_script_path}")
    
    def _test_nas_connection(self, ip: str, port: int) -> bool:
        """测试NAS连接"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except:
            return False
    
    def _is_current_machine(self, tailscale_ip: str) -> bool:
        """检测是否为当前机器"""
        try:
            # 简单的方法：尝试绑定该IP
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind((tailscale_ip, 0))
            sock.close()
            return True
        except:
            return False
    
    def run_wizard(self):
        """运行配置向导"""
        self.welcome()
        
        # 1. 检测环境
        env_info = self.detect_current_environment()
        
        # 2. 配置部署模式
        mode = self.configure_deployment_mode()
        
        # 3. 配置NAS连接
        nas_config = self.configure_nas_connection(env_info)
        
        # 4. 配置路径
        paths = self.configure_paths(mode)
        
        # 5. 配置处理设置
        settings = self.configure_processing_settings()
        
        # 6. 如果是中介模式，配置中介设置
        bridge_config = None
        if mode == "bridge":
            bridge_config = self.configure_bridge_mode(env_info)
        
        # 7. 生成配置文件
        self.generate_config_files(mode, nas_config, paths, settings, bridge_config)
        
        # 8. 显示完成信息
        self.show_completion_info(mode)
    
    def show_completion_info(self, mode: str):
        """显示完成信息"""
        print("\n🎉 配置向导完成！")
        print("=" * 60)
        print("配置文件已生成，您可以:")
        print("1. 检查并修改 config/config.py 中的配置")
        
        if mode == "bridge":
            print("2. 检查并修改 config/bridge_config.py 中的中介配置")
            print("3. 运行中介传输工具: python3 tools/bridge_transfer.py")
        else:
            print("2. 运行环境检查: python3 tools/check_environment.py")
            print("3. 启动处理程序: bash run.sh")
        
        print("\n📚 更多信息请查看:")
        print("  - README.md: 项目说明")
        print("  - doc/部署指南.md: 部署指南")
        print("  - doc/绿联云SSH启用指南.md: SSH配置指南")
        print("=" * 60)


def main():
    """主函数"""
    from datetime import datetime
    
    wizard = SetupWizard()
    wizard.run_wizard()


if __name__ == "__main__":
    main() 