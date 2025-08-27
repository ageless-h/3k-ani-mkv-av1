#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import urllib.request
import urllib.parse
from typing import List, Optional
from pathlib import Path
from utils import setup_logging

class NASConnector:
    """通过tailscale网络连接访问NAS的工具类"""
    
    def __init__(self, nas_ip="100.74.107.59", logger=None):
        self.nas_ip = nas_ip
        self.logger = logger or setup_logging()
        
    def test_connection(self) -> bool:
        """测试与NAS的网络连接"""
        try:
            import socket
            
            # 使用socket测试连接（更适合容器环境）
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            
            # 尝试连接SSH端口22
            result = sock.connect_ex((self.nas_ip, 22))
            sock.close()
            
            if result == 0:
                self.logger.info(f"NAS连接正常: {self.nas_ip}")
                return True
            else:
                self.logger.warning(f"NAS连接失败: {self.nas_ip} (端口22不可达)")
                # 尝试简单的SSH测试
                try:
                    test_result = subprocess.run(
                        ['ssh', '-o', 'ConnectTimeout=5', '-o', 'BatchMode=yes', 
                         f'root@{self.nas_ip}', 'echo "test"'],
                        capture_output=True,
                        timeout=10
                    )
                    if test_result.returncode == 0:
                        self.logger.info(f"SSH连接正常: {self.nas_ip}")
                        return True
                except:
                    pass
                return False
                
        except Exception as e:
            self.logger.error(f"网络连接测试出错: {str(e)}")
            # 如果网络测试失败，尝试直接测试SSH
            try:
                self.logger.info("回退到SSH连接测试...")
                test_result = subprocess.run(
                    ['ssh', '-o', 'ConnectTimeout=3', '-o', 'BatchMode=yes',
                     f'root@{self.nas_ip}', 'echo "test"'],
                    capture_output=True,
                    timeout=8
                )
                if test_result.returncode == 0:
                    self.logger.info(f"SSH连接正常: {self.nas_ip}")
                    return True
                else:
                    self.logger.warning(f"SSH连接失败: {test_result.stderr.decode()}")
                    return False
            except Exception as ssh_e:
                self.logger.error(f"SSH测试也失败: {str(ssh_e)}")
                return False
    
    def check_tailscale_status(self) -> dict:
        """检查tailscale连接状态"""
        try:
            result = subprocess.run(
                ['tailscale', 'status'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                devices = {}
                
                for line in lines:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 2:
                            ip = parts[0]
                            name = parts[1]
                            devices[name] = ip
                
                self.logger.info(f"Tailscale设备: {devices}")
                return devices
            else:
                self.logger.warning("无法获取tailscale状态")
                return {}
                
        except Exception as e:
            self.logger.error(f"Tailscale状态检查出错: {str(e)}")
            return {}
    
    def copy_file_from_nas(self, remote_path: str, local_path: str) -> bool:
        """从NAS复制单个文件到本地"""
        try:
            # 尝试使用scp
            scp_command = [
                'scp',
                f'root@{self.nas_ip}:{remote_path}',
                local_path
            ]
            
            self.logger.debug(f"SCP命令: {' '.join(scp_command)}")
            
            result = subprocess.run(
                scp_command,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            if result.returncode == 0:
                self.logger.info(f"文件复制成功: {remote_path} -> {local_path}")
                return True
            else:
                self.logger.error(f"SCP复制失败: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"文件复制出错: {str(e)}")
            return False
    
    def sync_file_to_nas(self, local_path: str, remote_path: str) -> bool:
        """将本地文件同步到NAS"""
        try:
            # 确保远程目录存在
            remote_dir = os.path.dirname(remote_path)
            mkdir_command = [
                'ssh',
                f'root@{self.nas_ip}',
                f'mkdir -p "{remote_dir}"'
            ]
            
            subprocess.run(mkdir_command, capture_output=True, timeout=30)
            
            # 使用scp传输文件
            scp_command = [
                'scp',
                local_path,
                f'root@{self.nas_ip}:{remote_path}'
            ]
            
            self.logger.debug(f"SCP上传命令: {' '.join(scp_command)}")
            
            result = subprocess.run(
                scp_command,
                capture_output=True,
                text=True,
                timeout=600  # 10分钟超时
            )
            
            if result.returncode == 0:
                self.logger.info(f"文件上传成功: {local_path} -> {remote_path}")
                return True
            else:
                self.logger.error(f"SCP上传失败: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"文件上传出错: {str(e)}")
            return False
    
    def check_remote_file_exists(self, remote_path: str) -> bool:
        """检查NAS上的文件是否存在"""
        try:
            check_command = [
                'ssh',
                f'root@{self.nas_ip}',
                f'test -f "{remote_path}" && echo "exists" || echo "not_found"'
            ]
            
            result = subprocess.run(
                check_command,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return "exists" in result.stdout.strip()
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"远程文件检查出错: {str(e)}")
            return False
    
    def get_file_size(self, remote_path: str) -> int:
        """获取NAS上文件的大小"""
        try:
            size_command = [
                'ssh',
                f'root@{self.nas_ip}',
                f'stat -c%s "{remote_path}"'
            ]
            
            result = subprocess.run(
                size_command,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return int(result.stdout.strip())
            else:
                return 0
                
        except Exception as e:
            self.logger.error(f"获取文件大小出错: {str(e)}")
            return 0

class LocalProcessor:
    """本地处理器，先在本地处理，再传输到NAS"""
    
    def __init__(self, nas_connector: NASConnector = None, logger=None):
        self.nas_connector = nas_connector or NASConnector()
        self.logger = logger or setup_logging()
        
    def process_video_locally(self, video_info: dict, local_temp_dir: str) -> Optional[str]:
        """在本地处理视频（如果视频已下载）"""
        try:
            video_path = video_info.get('path', '')
            video_name = os.path.basename(video_path)
            
            # 检查本地是否已有视频文件
            local_video_path = os.path.join(local_temp_dir, video_name)
            
            if not os.path.exists(local_video_path):
                self.logger.info(f"需要从NAS下载视频: {video_path}")
                
                # 尝试从NAS下载视频
                if not self.nas_connector.copy_file_from_nas(video_path, local_video_path):
                    self.logger.error(f"视频下载失败: {video_path}")
                    return None
            
            # 返回本地视频路径用于处理
            return local_video_path
            
        except Exception as e:
            self.logger.error(f"本地视频处理准备出错: {str(e)}")
            return None
    
    def upload_results_to_nas(self, local_archive_path: str, nas_output_dir: str) -> bool:
        """将处理结果上传到NAS"""
        try:
            archive_name = os.path.basename(local_archive_path)
            remote_archive_path = os.path.join(nas_output_dir, archive_name)
            
            self.logger.info(f"开始上传结果到NAS: {archive_name}")
            
            success = self.nas_connector.sync_file_to_nas(
                local_archive_path, 
                remote_archive_path
            )
            
            if success:
                # 验证上传
                if self.nas_connector.check_remote_file_exists(remote_archive_path):
                    self.logger.info(f"结果上传成功: {remote_archive_path}")
                    
                    # 清理本地文件
                    try:
                        os.remove(local_archive_path)
                        self.logger.info(f"本地文件已清理: {local_archive_path}")
                    except:
                        pass
                    
                    return True
                else:
                    self.logger.error("上传验证失败")
                    return False
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"结果上传出错: {str(e)}")
            return False

def setup_ssh_key_auth(nas_ip: str) -> bool:
    """设置SSH密钥认证（如果需要）"""
    try:
        # 检查是否已有SSH密钥
        ssh_key_path = os.path.expanduser("~/.ssh/id_rsa")
        
        if not os.path.exists(ssh_key_path):
            print("请先设置SSH密钥认证:")
            print(f"1. ssh-keygen -t rsa -b 4096")
            print(f"2. ssh-copy-id root@{nas_ip}")
            return False
        
        # 测试SSH连接
        test_command = ['ssh', '-o', 'ConnectTimeout=5', f'root@{nas_ip}', 'echo "test"']
        result = subprocess.run(test_command, capture_output=True, timeout=10)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"SSH设置检查出错: {str(e)}")
        return False 