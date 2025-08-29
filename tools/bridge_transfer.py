#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
中介传输工具
在waas服务器和NAS之间建立数据传输桥梁
"""

import os
import sys
import time
import socket
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.bridge_config import BridgeConfig
from src.utils import setup_logging


class BridgeTransfer:
    """中介传输管理器"""
    
    def __init__(self, logger=None):
        self.logger = logger or setup_logging()
        self.config = BridgeConfig()
        
    def test_network_connectivity(self) -> Dict[str, bool]:
        """测试网络连通性"""
        self.logger.info("测试网络连通性...")
        
        results = {
            'nas': False,
            'waas': False
        }
        
        # 测试NAS连接
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            result = sock.connect_ex((self.config.NAS_IP, self.config.NAS_SSH_PORT))
            sock.close()
            
            if result == 0:
                results['nas'] = True
                self.logger.info(f"✅ NAS连接正常: {self.config.NAS_IP}:{self.config.NAS_SSH_PORT}")
            else:
                self.logger.error(f"❌ NAS连接失败: {self.config.NAS_IP}:{self.config.NAS_SSH_PORT}")
                
        except Exception as e:
            self.logger.error(f"❌ NAS连接测试异常: {str(e)}")
        
        # 测试waas连接
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            result = sock.connect_ex((self.config.WAAS_IP, self.config.WAAS_SSH_PORT))
            sock.close()
            
            if result == 0:
                results['waas'] = True
                self.logger.info(f"✅ waas连接正常: {self.config.WAAS_IP}:{self.config.WAAS_SSH_PORT}")
            else:
                self.logger.error(f"❌ waas连接失败: {self.config.WAAS_IP}:{self.config.WAAS_SSH_PORT}")
                
        except Exception as e:
            self.logger.error(f"❌ waas连接测试异常: {str(e)}")
        
        return results
    
    def test_ssh_connection(self, target: str) -> bool:
        """测试SSH连接"""
        self.logger.info(f"测试SSH连接: {target}")
        
        try:
            ssh_cmd = self.config.get_ssh_command_prefix(target)
            test_cmd = f"{ssh_cmd} 'echo SSH连接测试成功'"
            
            result = subprocess.run(
                test_cmd, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if result.returncode == 0:
                self.logger.info(f"✅ {target} SSH连接成功")
                return True
            else:
                self.logger.error(f"❌ {target} SSH连接失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"❌ {target} SSH连接超时")
            return False
        except Exception as e:
            self.logger.error(f"❌ {target} SSH连接异常: {str(e)}")
            return False
    
    def get_file_list_from_nas(self, remote_dir: str = None) -> List[str]:
        """从NAS获取文件列表"""
        if remote_dir is None:
            remote_dir = self.config.NAS_SOURCE_DIR
            
        self.logger.info(f"获取NAS文件列表: {remote_dir}")
        
        try:
            ssh_cmd = self.config.get_ssh_command_prefix("nas")
            list_cmd = f"{ssh_cmd} 'find {remote_dir} -type f -name \"*.mkv\" -o -name \"*.mp4\" -o -name \"*.avi\" | head -20'"
            
            result = subprocess.run(
                list_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
                self.logger.info(f"找到 {len(files)} 个视频文件")
                return files
            else:
                self.logger.error(f"获取文件列表失败: {result.stderr}")
                return []
                
        except Exception as e:
            self.logger.error(f"获取文件列表异常: {str(e)}")
            return []
    
    def transfer_file_to_waas(self, nas_file_path: str, waas_target_dir: str = None) -> bool:
        """从NAS传输文件到waas"""
        if waas_target_dir is None:
            waas_target_dir = self.config.WAAS_TEMP_DIR
            
        file_name = os.path.basename(nas_file_path)
        waas_target_path = f"{waas_target_dir}/{file_name}"
        
        self.logger.info(f"传输文件: {nas_file_path} -> waas:{waas_target_path}")
        
        # 确保waas目标目录存在
        if not self._ensure_waas_directory(waas_target_dir):
            return False
        
        # 尝试不同的传输方法
        for method in self.config.TRANSFER_METHODS:
            if self._transfer_with_method(method, "nas", nas_file_path, "waas", waas_target_path):
                self.logger.info(f"✅ 文件传输成功: {file_name}")
                return True
        
        self.logger.error(f"❌ 文件传输失败: {file_name}")
        return False
    
    def transfer_result_from_waas(self, waas_file_path: str, nas_target_dir: str = None) -> bool:
        """从waas传输处理结果到NAS"""
        if nas_target_dir is None:
            nas_target_dir = self.config.NAS_OUTPUT_DIR
            
        file_name = os.path.basename(waas_file_path)
        nas_target_path = f"{nas_target_dir}/{file_name}"
        
        self.logger.info(f"传输结果: waas:{waas_file_path} -> {nas_target_path}")
        
        # 确保NAS目标目录存在
        if not self._ensure_nas_directory(nas_target_dir):
            return False
        
        # 尝试不同的传输方法
        for method in self.config.TRANSFER_METHODS:
            if self._transfer_with_method(method, "waas", waas_file_path, "nas", nas_target_path):
                self.logger.info(f"✅ 结果传输成功: {file_name}")
                return True
        
        self.logger.error(f"❌ 结果传输失败: {file_name}")
        return False
    
    def _ensure_waas_directory(self, directory: str) -> bool:
        """确保waas目录存在"""
        try:
            ssh_cmd = self.config.get_ssh_command_prefix("waas")
            mkdir_cmd = f"{ssh_cmd} 'mkdir -p {directory}'"
            
            result = subprocess.run(mkdir_cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"创建waas目录失败: {str(e)}")
            return False
    
    def _ensure_nas_directory(self, directory: str) -> bool:
        """确保NAS目录存在"""
        try:
            ssh_cmd = self.config.get_ssh_command_prefix("nas")
            mkdir_cmd = f"{ssh_cmd} 'mkdir -p {directory}'"
            
            result = subprocess.run(mkdir_cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"创建NAS目录失败: {str(e)}")
            return False
    
    def _transfer_with_method(self, method: str, src_target: str, src_path: str, 
                             dst_target: str, dst_path: str) -> bool:
        """使用指定方法传输文件"""
        try:
            if method == "rsync":
                return self._rsync_transfer(src_target, src_path, dst_target, dst_path)
            elif method == "scp":
                return self._scp_transfer(src_target, src_path, dst_target, dst_path)
            elif method == "sftp":
                return self._sftp_transfer(src_target, src_path, dst_target, dst_path)
            else:
                self.logger.error(f"不支持的传输方法: {method}")
                return False
        except Exception as e:
            self.logger.error(f"{method}传输失败: {str(e)}")
            return False
    
    def _rsync_transfer(self, src_target: str, src_path: str, dst_target: str, dst_path: str) -> bool:
        """使用rsync传输"""
        if src_target == "nas":
            src_full = f"{self.config.get_nas_ssh_target()}:{src_path}"
            rsync_cmd = self.config.get_rsync_command_prefix("waas")
            dst_full = f"{self.config.get_waas_ssh_target()}:{dst_path}"
        else:
            src_full = f"{self.config.get_waas_ssh_target()}:{src_path}"
            rsync_cmd = self.config.get_rsync_command_prefix("nas")
            dst_full = f"{self.config.get_nas_ssh_target()}:{dst_path}"
        
        cmd = f"{rsync_cmd} {src_full} {dst_full}"
        
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=self.config.TRANSFER_TIMEOUT
        )
        
        return result.returncode == 0
    
    def _scp_transfer(self, src_target: str, src_path: str, dst_target: str, dst_path: str) -> bool:
        """使用scp传输"""
        if src_target == "nas":
            src_full = f"{self.config.get_nas_ssh_target()}:{src_path}"
            scp_cmd = self.config.get_scp_command_prefix("waas")
            dst_full = f"{self.config.get_waas_ssh_target()}:{dst_path}"
        else:
            src_full = f"{self.config.get_waas_ssh_target()}:{src_path}"
            scp_cmd = self.config.get_scp_command_prefix("nas") 
            dst_full = f"{self.config.get_nas_ssh_target()}:{dst_path}"
        
        cmd = f"{scp_cmd} {src_full} {dst_full}"
        
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=self.config.TRANSFER_TIMEOUT
        )
        
        return result.returncode == 0
    
    def _sftp_transfer(self, src_target: str, src_path: str, dst_target: str, dst_path: str) -> bool:
        """使用sftp传输 (简化实现)"""
        # 这里可以实现sftp传输逻辑
        # 为简化演示，返回False
        self.logger.warning("SFTP传输尚未实现")
        return False
    
    def start_processing_on_waas(self, video_files: List[str]) -> bool:
        """在waas上启动处理任务"""
        self.logger.info(f"在waas上启动处理任务，包含 {len(video_files)} 个文件")
        
        try:
            # 创建临时文件列表
            file_list_content = "\n".join(video_files)
            
            # 将文件列表传输到waas
            ssh_cmd = self.config.get_ssh_command_prefix("waas")
            upload_cmd = f"echo '{file_list_content}' | {ssh_cmd} 'cat > {self.config.WAAS_PROJECT_DIR}/current_batch.txt'"
            
            result = subprocess.run(upload_cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"文件列表上传失败: {result.stderr}")
                return False
            
            # 启动处理程序
            start_cmd = f"{ssh_cmd} 'cd {self.config.WAAS_PROJECT_DIR} && nohup bash run.sh > processing.log 2>&1 &'"
            
            result = subprocess.run(start_cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info("✅ waas处理任务启动成功")
                return True
            else:
                self.logger.error(f"❌ waas处理任务启动失败: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"启动waas处理任务异常: {str(e)}")
            return False
    
    def monitor_waas_processing(self) -> str:
        """监控waas处理状态"""
        try:
            ssh_cmd = self.config.get_ssh_command_prefix("waas")
            status_cmd = f"{ssh_cmd} 'cd {self.config.WAAS_PROJECT_DIR} && tail -20 processing.log'"
            
            result = subprocess.run(status_cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                return result.stdout
            else:
                return f"获取状态失败: {result.stderr}"
                
        except Exception as e:
            return f"监控异常: {str(e)}"


def main():
    """主函数"""
    print("🌉 中介传输工具")
    print("=" * 50)
    
    bridge = BridgeTransfer()
    
    # 1. 测试网络连通性
    print("\n1. 测试网络连通性...")
    connectivity = bridge.test_network_connectivity()
    
    if not all(connectivity.values()):
        print("❌ 网络连通性测试失败，请检查Tailscale连接")
        return
    
    # 2. 测试SSH连接
    print("\n2. 测试SSH连接...")
    nas_ssh = bridge.test_ssh_connection("nas")
    waas_ssh = bridge.test_ssh_connection("waas")
    
    if not (nas_ssh and waas_ssh):
        print("❌ SSH连接测试失败，请检查SSH配置")
        return
    
    # 3. 获取文件列表示例
    print("\n3. 获取NAS文件列表示例...")
    files = bridge.get_file_list_from_nas()
    
    if files:
        print(f"✅ 找到 {len(files)} 个文件")
        for i, file in enumerate(files[:5]):
            print(f"  {i+1}. {file}")
        if len(files) > 5:
            print(f"  ... 还有 {len(files)-5} 个文件")
    else:
        print("⚠️  未找到文件或连接失败")
    
    # 4. 传输测试 (可选)
    print("\n4. 传输功能已就绪")
    print("   使用方法:")
    print("   - bridge.transfer_file_to_waas(nas_file_path)")
    print("   - bridge.start_processing_on_waas(video_files)")
    print("   - bridge.transfer_result_from_waas(waas_result_path)")
    
    print("\n✅ 中介传输工具测试完成")


if __name__ == "__main__":
    main() 