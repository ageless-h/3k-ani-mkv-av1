#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
3K动画处理系统部署脚本
用于在Linux服务器上快速部署和配置项目
"""

import os
import sys
import subprocess
import urllib.request
from pathlib import Path


class ProjectDeployer:
    """项目部署器"""
    
    def __init__(self):
        self.project_dir = Path.cwd()
        self.venv_dir = self.project_dir / "venv"
        
    def welcome(self):
        """欢迎信息"""
        print("🚀 3K动画处理系统部署脚本")
        print("=" * 50)
        print("此脚本将帮助您在Linux服务器上部署项目")
        print("=" * 50)
        print()
    
    def check_system_requirements(self) -> bool:
        """检查系统要求"""
        print("🔍 检查系统要求...")
        
        # 检查Python版本
        if sys.version_info < (3, 8):
            print("❌ Python版本过低，需要Python 3.8+")
            return False
        print(f"✅ Python版本: {sys.version.split()[0]}")
        
        # 检查必要的系统命令
        required_commands = ['git', 'ffmpeg', 'pip3']
        missing_commands = []
        
        for cmd in required_commands:
            if not self._command_exists(cmd):
                missing_commands.append(cmd)
        
        if missing_commands:
            print(f"❌ 缺少必要命令: {', '.join(missing_commands)}")
            self._suggest_package_installation(missing_commands)
            return False
        
        print("✅ 系统命令检查通过")
        return True
    
    def setup_virtual_environment(self):
        """设置虚拟环境"""
        print("\n🐍 设置Python虚拟环境...")
        
        if self.venv_dir.exists():
            print("⚠️  虚拟环境已存在，跳过创建")
        else:
            # 创建虚拟环境
            result = subprocess.run([sys.executable, '-m', 'venv', str(self.venv_dir)])
            if result.returncode != 0:
                print("❌ 虚拟环境创建失败")
                return False
            print("✅ 虚拟环境创建成功")
        
        # 激活虚拟环境并安装依赖
        pip_path = self.venv_dir / "bin" / "pip"
        if not pip_path.exists():
            print("❌ 找不到虚拟环境pip")
            return False
        
        # 升级pip
        subprocess.run([str(pip_path), 'install', '--upgrade', 'pip'])
        
        # 安装项目依赖
        requirements_file = self.project_dir / "requirements.txt"
        if requirements_file.exists():
            print("📦 安装Python依赖...")
            result = subprocess.run([str(pip_path), 'install', '-r', str(requirements_file)])
            if result.returncode == 0:
                print("✅ Python依赖安装成功")
            else:
                print("❌ Python依赖安装失败")
                return False
        
        return True
    
    def setup_libwebp(self):
        """设置libwebp"""
        print("\n🖼️  设置libwebp...")
        
        libwebp_dir = self.project_dir / "libwebp"
        if libwebp_dir.exists():
            print("⚠️  libwebp已存在，跳过安装")
            return True
        
        # 运行libwebp安装脚本
        install_script = self.project_dir / "tools" / "install_libwebp.sh"
        if install_script.exists():
            result = subprocess.run(['bash', str(install_script)])
            if result.returncode == 0:
                print("✅ libwebp安装成功")
                return True
            else:
                print("⚠️  libwebp安装失败，将使用Pillow备用方案")
                return True  # 不是致命错误
        else:
            print("⚠️  未找到libwebp安装脚本")
            return True
    
    def setup_directories(self):
        """设置目录结构"""
        print("\n📁 设置目录结构...")
        
        # 创建必要的目录
        directories = [
            "log",
            "output",
            "output/animation", 
            "output/video",
            "/tmp/animation_processing"
        ]
        
        for dir_path in directories:
            path = Path(dir_path)
            if not path.is_absolute():
                path = self.project_dir / dir_path
            
            try:
                path.mkdir(parents=True, exist_ok=True)
                print(f"✅ 创建目录: {path}")
            except Exception as e:
                print(f"⚠️  创建目录失败 {path}: {e}")
        
        return True
    
    def setup_configuration(self):
        """设置配置"""
        print("\n⚙️  设置配置...")
        
        config_file = self.project_dir / "config" / "config.py"
        config_example = self.project_dir / "config" / "config_example.py"
        
        if config_file.exists():
            print("⚠️  配置文件已存在，跳过复制")
        elif config_example.exists():
            # 复制示例配置
            import shutil
            shutil.copy2(config_example, config_file)
            print("✅ 复制示例配置文件")
            print("⚠️  请编辑 config/config.py 设置您的具体配置")
        else:
            print("❌ 未找到配置文件模板")
            return False
        
        return True
    
    def run_configuration_wizard(self):
        """配置检查"""
        print("\n✅ 配置检查")
        print("魔搭社区模式使用默认配置，无需额外配置向导")
        print("如需修改配置，请编辑 config/config.py")
        print("主要配置项：")
        print("  - MODELSCOPE_TOKEN: 魔搭社区访问令牌")
        print("  - MAX_EPISODES_PER_BATCH: 每批处理的视频数量")
        print("  - MIN_FREE_SPACE_GB: 最小保留磁盘空间")
        return True
    
    def create_systemd_service(self):
        """创建systemd服务文件"""
        print("\n🔧 是否创建systemd服务？")
        choice = input("创建系统服务可以让程序开机自启 (y/n) [n]: ").strip().lower()
        
        if choice == 'y':
            service_content = f"""[Unit]
Description=3K Animation Processing System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={self.project_dir}
Environment=PATH={self.venv_dir}/bin:/usr/local/bin:/usr/bin:/bin
ExecStart={self.venv_dir}/bin/python -m src.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
            
            service_file = Path("/etc/systemd/system/3k-animation.service")
            try:
                with open(service_file, 'w') as f:
                    f.write(service_content)
                
                # 重新加载systemd并启用服务
                subprocess.run(['systemctl', 'daemon-reload'])
                subprocess.run(['systemctl', 'enable', '3k-animation'])
                
                print("✅ systemd服务创建成功")
                print("使用以下命令控制服务:")
                print("  启动: systemctl start 3k-animation")
                print("  停止: systemctl stop 3k-animation")
                print("  查看状态: systemctl status 3k-animation")
                print("  查看日志: journalctl -u 3k-animation -f")
                
            except Exception as e:
                print(f"❌ 创建systemd服务失败: {e}")
        
        return True
    
    def run_environment_check(self):
        """运行环境检查"""
        print("\n🔍 运行环境检查...")
        
        check_script = self.project_dir / "tools" / "check_environment.py"
        if check_script.exists():
            result = subprocess.run([sys.executable, str(check_script)])
            if result.returncode == 0:
                print("✅ 环境检查通过")
            else:
                print("⚠️  环境检查发现问题，请查看上方输出")
        else:
            print("⚠️  未找到环境检查脚本")
        
        return True
    
    def show_completion_info(self):
        """显示完成信息"""
        print("\n🎉 部署完成！")
        print("=" * 50)
        print("项目已成功部署，您可以:")
        print("")
        print("1. 运行环境检查:")
        print("   python3 tools/check_environment.py")
        print("")
        print("2. 编辑配置文件:")
        print("   vim config/config.py")
        print("")
        print("3. 启动自动监控:")
        print("   bash start_monitoring.sh")
        print("")
        print("4. 启动处理程序:")
        print("   bash run.sh")
        print("")
        print("5. 后台运行:")
        print("   nohup bash run.sh > processing.log 2>&1 &")
        print("")
        print("6. 查看日志:")
        print("   tail -f log/processing.log")
        print("")
        print("📚 更多信息请查看 README.md 和 doc/ 目录下的文档")
        print("=" * 50)
    
    def _command_exists(self, command: str) -> bool:
        """检查命令是否存在"""
        try:
            subprocess.run(['which', command], 
                         capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def _suggest_package_installation(self, missing_commands: list):
        """建议包安装"""
        print("\n💡 安装建议:")
        
        # Ubuntu/Debian
        ubuntu_packages = {
            'git': 'git',
            'ffmpeg': 'ffmpeg',
            'pip3': 'python3-pip'
        }
        
        ubuntu_cmd = "sudo apt update && sudo apt install -y " + " ".join(
            ubuntu_packages.get(cmd, cmd) for cmd in missing_commands
        )
        print(f"Ubuntu/Debian: {ubuntu_cmd}")
        
        # CentOS/RHEL
        centos_packages = {
            'git': 'git',
            'ffmpeg': 'ffmpeg',
            'pip3': 'python3-pip'
        }
        
        centos_cmd = "sudo yum install -y " + " ".join(
            centos_packages.get(cmd, cmd) for cmd in missing_commands
        )
        print(f"CentOS/RHEL: {centos_cmd}")
    
    def deploy(self):
        """执行部署"""
        self.welcome()
        
        # 1. 检查系统要求
        if not self.check_system_requirements():
            print("\n❌ 系统要求检查失败，请安装必要的软件后重试")
            return False
        
        # 2. 设置虚拟环境
        if not self.setup_virtual_environment():
            print("\n❌ 虚拟环境设置失败")
            return False
        
        # 3. 设置libwebp
        self.setup_libwebp()
        
        # 4. 设置目录结构
        self.setup_directories()
        
        # 5. 设置配置
        if not self.setup_configuration():
            print("\n❌ 配置设置失败")
            return False
        
        # 6. 运行配置向导
        self.run_configuration_wizard()
        
        # 7. 创建systemd服务 (可选)
        self.create_systemd_service()
        
        # 8. 运行环境检查
        self.run_environment_check()
        
        # 9. 显示完成信息
        self.show_completion_info()
        
        return True


def main():
    """主函数"""
    deployer = ProjectDeployer()
    success = deployer.deploy()
    
    if success:
        print("\n🎯 部署成功完成！")
        sys.exit(0)
    else:
        print("\n💥 部署过程中遇到错误")
        sys.exit(1)


if __name__ == "__main__":
    main() 