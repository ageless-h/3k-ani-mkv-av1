#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
中介终端机配置
用于在waas服务器和NAS之间建立数据传输中介
"""

class BridgeConfig:
    """中介传输配置"""
    
    # === 网络拓扑配置 ===
    # NAS设备信息
    NAS_NAME = "dh4300plus-0e7a"
    NAS_IP = "100.121.135.47"  # NAS在Tailscale网络中的IP
    NAS_SSH_PORT = 22
    NAS_SSH_USER = "root"  # 或 "admin", "ugos"
    
    # waas处理服务器信息  
    WAAS_NAME = "waas"
    WAAS_IP = "100.95.10.55"   # waas在Tailscale网络中的IP
    WAAS_SSH_PORT = 22
    WAAS_SSH_USER = "root"
    
    # Windows中介终端机信息
    BRIDGE_NAME = "win-fjcmcrnsif0"
    BRIDGE_IP = "100.69.148.34"  # Windows中介机在Tailscale网络中的IP
    
    # === 路径配置 ===
    # NAS上的源路径
    NAS_SOURCE_DIR = "/volume1/db/5_video/archive"
    NAS_OUTPUT_DIR = "/volume1/db/1_ai/data/image/animation"
    
    # waas服务器上的路径
    WAAS_TEMP_DIR = "/tmp/animation_processing"
    WAAS_OUTPUT_DIR = "/root/output/animation" 
    WAAS_PROJECT_DIR = "/root/3k-ani-mkv-av1"
    
    # Windows中介机上的临时路径 (如果需要)
    BRIDGE_TEMP_DIR = "C:\\temp\\animation_bridge"
    
    # === 传输配置 ===
    # 传输方式优先级
    TRANSFER_METHODS = [
        "rsync",  # 首选rsync (支持断点续传)
        "scp",    # 备选scp
        "sftp"    # 最后选择sftp
    ]
    
    # 批量传输配置
    MAX_CONCURRENT_TRANSFERS = 2    # 最大并发传输数
    TRANSFER_TIMEOUT = 300          # 传输超时时间 (秒)
    RETRY_COUNT = 3                 # 重试次数
    
    # 文件大小限制
    MAX_FILE_SIZE_GB = 50           # 单文件最大大小 (GB)
    BATCH_SIZE_GB = 100             # 批次总大小限制 (GB)
    
    # === SSH配置 ===
    # SSH密钥路径 (如果使用密钥认证)
    SSH_KEY_PATH = "~/.ssh/id_rsa"
    
    # SSH连接选项
    SSH_OPTIONS = [
        "-o ConnectTimeout=30",
        "-o ServerAliveInterval=60", 
        "-o ServerAliveCountMax=3",
        "-o StrictHostKeyChecking=no",
        "-o UserKnownHostsFile=/dev/null"
    ]
    
    # === 监控配置 ===
    # 传输进度监控
    PROGRESS_UPDATE_INTERVAL = 5    # 进度更新间隔 (秒)
    LOG_LEVEL = "INFO"              # 日志级别
    
    # 网络质量检测
    NETWORK_TEST_INTERVAL = 300     # 网络测试间隔 (秒)
    MIN_BANDWIDTH_MBPS = 10         # 最小带宽要求 (Mbps)
    
    # === 存储配置 ===
    # 磁盘空间检查
    MIN_FREE_SPACE_GB = 10          # 最小剩余空间 (GB)
    CLEANUP_THRESHOLD_GB = 5        # 清理阈值 (GB)
    
    @classmethod
    def get_nas_ssh_target(cls):
        """获取NAS SSH连接目标"""
        return f"{cls.NAS_SSH_USER}@{cls.NAS_IP}"
    
    @classmethod  
    def get_waas_ssh_target(cls):
        """获取waas SSH连接目标"""
        return f"{cls.WAAS_SSH_USER}@{cls.WAAS_IP}"
    
    @classmethod
    def get_ssh_command_prefix(cls, target="nas"):
        """获取SSH命令前缀"""
        if target == "nas":
            host = cls.get_nas_ssh_target()
            port = cls.NAS_SSH_PORT
        elif target == "waas":
            host = cls.get_waas_ssh_target() 
            port = cls.WAAS_SSH_PORT
        else:
            raise ValueError(f"未知目标: {target}")
        
        options = " ".join(cls.SSH_OPTIONS)
        return f"ssh {options} -p {port} {host}"
    
    @classmethod
    def get_scp_command_prefix(cls, target="nas"):
        """获取SCP命令前缀"""
        if target == "nas":
            host = cls.get_nas_ssh_target()
            port = cls.NAS_SSH_PORT
        elif target == "waas":
            host = cls.get_waas_ssh_target()
            port = cls.WAAS_SSH_PORT
        else:
            raise ValueError(f"未知目标: {target}")
        
        options = " ".join(cls.SSH_OPTIONS)
        return f"scp {options} -P {port}"
    
    @classmethod
    def get_rsync_command_prefix(cls, target="nas"):
        """获取rsync命令前缀"""
        if target == "nas":
            host = cls.get_nas_ssh_target()
            port = cls.NAS_SSH_PORT
        elif target == "waas": 
            host = cls.get_waas_ssh_target()
            port = cls.WAAS_SSH_PORT
        else:
            raise ValueError(f"未知目标: {target}")
        
        ssh_opts = " ".join(cls.SSH_OPTIONS)
        return f"rsync -avz --progress -e 'ssh {ssh_opts} -p {port}'" 