#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NAS连接诊断工具
用于诊断服务器到NAS的网络连接问题
"""

import socket
import subprocess
import sys
from network_utils import NASConnector
from utils import setup_logging

def diagnose_network():
    """全面诊断网络连接"""
    logger = setup_logging()
    nas_ip = "100.74.107.59"
    
    print("🔍 NAS连接诊断工具")
    print("=" * 50)
    
    # 1. 基础网络测试
    print("\n1. 基础网络连通性测试")
    print("-" * 30)
    
    # Tailscale状态
    try:
        result = subprocess.run(['tailscale', 'status'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Tailscale状态正常")
            for line in result.stdout.split('\n'):
                if nas_ip in line:
                    print(f"   {line}")
        else:
            print("❌ Tailscale状态异常")
    except Exception as e:
        print(f"❌ 无法获取Tailscale状态: {str(e)}")
    
    # 2. 端口扫描
    print("\n2. 端口扫描测试")
    print("-" * 30)
    
    common_ports = {
        22: "SSH",
        80: "HTTP", 
        443: "HTTPS",
        21: "FTP",
        23: "Telnet",
        139: "NetBIOS",
        445: "SMB/CIFS",
        111: "Portmapper",
        2049: "NFS",
        8080: "HTTP-Alt",
        8443: "HTTPS-Alt"
    }
    
    open_ports = []
    for port, service in common_ports.items():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((nas_ip, port))
            sock.close()
            
            if result == 0:
                print(f"✅ 端口 {port:5d} ({service:10s}) - 开放")
                open_ports.append(port)
            else:
                print(f"❌ 端口 {port:5d} ({service:10s}) - 关闭/过滤")
        except Exception as e:
            print(f"❌ 端口 {port:5d} ({service:10s}) - 错误: {str(e)}")
    
    # 3. SSH详细测试
    print("\n3. SSH连接详细测试")
    print("-" * 30)
    
    if 22 in open_ports:
        print("✅ SSH端口22开放，测试连接...")
        
        # 测试SSH连接（不同参数）
        ssh_tests = [
            ['ssh', '-o', 'ConnectTimeout=5', '-o', 'BatchMode=yes', f'root@{nas_ip}', 'echo test'],
            ['ssh', '-o', 'ConnectTimeout=5', '-o', 'PasswordAuthentication=no', f'root@{nas_ip}', 'echo test'],
            ['ssh', '-o', 'ConnectTimeout=5', '-o', 'StrictHostKeyChecking=no', f'root@{nas_ip}', 'echo test'],
        ]
        
        for i, cmd in enumerate(ssh_tests, 1):
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                print(f"   测试{i}: 返回码={result.returncode}")
                if result.stderr:
                    print(f"   错误: {result.stderr.strip()}")
                if result.stdout:
                    print(f"   输出: {result.stdout.strip()}")
            except Exception as e:
                print(f"   测试{i}: 异常={str(e)}")
    else:
        print("❌ SSH端口22不开放")
    
    # 4. 网络路由测试
    print("\n4. 网络路由测试")
    print("-" * 30)
    
    # 尝试traceroute（如果有）
    try:
        result = subprocess.run(['traceroute', nas_ip], capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("✅ 路由跟踪成功:")
            for line in result.stdout.split('\n')[:5]:  # 只显示前5跳
                if line.strip():
                    print(f"   {line}")
        else:
            print("❌ 路由跟踪失败")
    except:
        print("⚠️  traceroute命令不可用")
    
    # 5. DNS解析测试
    print("\n5. DNS解析测试")
    print("-" * 30)
    
    try:
        import socket
        result = socket.gethostbyaddr(nas_ip)
        print(f"✅ 反向DNS解析成功: {result[0]}")
    except:
        print("⚠️  反向DNS解析失败（正常情况）")
    
    # 6. 使用NAS连接器测试
    print("\n6. NAS连接器测试")
    print("-" * 30)
    
    connector = NASConnector(nas_ip, logger=logger)
    if connector.test_connection():
        print("✅ NAS连接器测试通过")
    else:
        print("❌ NAS连接器测试失败")
    
    # 7. 建议
    print("\n7. 诊断建议")
    print("-" * 30)
    
    if not open_ports:
        print("❌ 未检测到任何开放端口")
        print("   建议：")
        print("   1. 检查NAS是否在线")
        print("   2. 检查Tailscale连接")
        print("   3. 检查NAS防火墙设置")
    elif 22 not in open_ports:
        print("⚠️  SSH端口22不可达")
        print("   建议：")
        print("   1. 在NAS上检查SSH服务状态: systemctl status ssh")
        print("   2. 检查SSH配置文件: /etc/ssh/sshd_config")
        print("   3. 检查NAS防火墙是否阻止了SSH")
        print("   4. 尝试重启SSH服务: systemctl restart ssh")
        
        if open_ports:
            print(f"   可考虑使用其他协议: {[common_ports[p] for p in open_ports]}")
    else:
        print("✅ SSH端口可达，可能是认证配置问题")
        print("   建议：")
        print("   1. 配置SSH密钥认证")
        print("   2. 检查SSH配置允许root登录")
        print("   3. 检查密码认证设置")

if __name__ == "__main__":
    diagnose_network() 