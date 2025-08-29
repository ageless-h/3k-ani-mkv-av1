# NAS SSH配置修复指南

## 🔍 问题分析

从诊断结果看，**错误代码11 (Connection refused)** 表示：
- ✅ **网络连通性正常** - Tailscale工作正常
- ❌ **NAS拒绝连接** - SSH服务或防火墙问题

## 🛠️ 在NAS上执行的修复步骤

### 1. 检查SSH服务状态
```bash
# 检查SSH服务是否运行
systemctl status ssh
# 或者
service ssh status

# 如果没有运行，启动它
systemctl start ssh
systemctl enable ssh  # 设置开机自启
```

### 2. 检查SSH配置文件
```bash
# 编辑SSH配置
nano /etc/ssh/sshd_config

# 确保以下配置正确：
Port 22
ListenAddress 0.0.0.0          # 监听所有接口
PermitRootLogin yes             # 允许root登录
PasswordAuthentication yes      # 允许密码认证
PubkeyAuthentication yes        # 允许密钥认证
```

### 3. 重启SSH服务
```bash
# 修改配置后重启SSH
systemctl restart ssh
# 或者
service ssh restart
```

### 4. 检查SSH监听状态
```bash
# 确认SSH正在监听端口22
netstat -tlnp | grep :22
# 或者
ss -tlnp | grep :22

# 应该看到类似这样的输出：
# tcp 0 0 0.0.0.0:22 0.0.0.0:* LISTEN 1234/sshd
```

### 5. 检查防火墙
```bash
# 检查iptables规则
iptables -L -n | grep 22

# 如果使用ufw
ufw status
ufw allow 22  # 允许SSH端口

# 如果使用firewalld
firewall-cmd --list-all
firewall-cmd --permanent --add-service=ssh
firewall-cmd --reload
```

### 6. 检查Tailscale配置
```bash
# 在NAS上检查Tailscale状态
tailscale status
tailscale ip -4  # 应该显示 100.74.107.59
```

## 🧪 测试修复结果

在**服务器上**执行：
```bash
# 拉取最新代码
cd ~/3k-ani-mkv-av1
git pull

# 重新运行诊断
python diagnose_nas.py

# 或者直接测试SSH
ssh -o ConnectTimeout=5 root@100.74.107.59 "echo 'SSH连接成功'"
```

## 📋 常见NAS系统的SSH启动方法

### Synology DSM
1. 控制面板 → 终端机和SNMP → 终端机
2. 启用SSH服务，端口22

### QNAP
1. 控制台 → 网络和虚拟交换机 → Telnet/SSH
2. 启用SSH连接，端口22

### FreeNAS/TrueNAS
1. 服务 → SSH
2. 启用服务，配置端口22

### OpenMediaVault
1. 服务 → SSH
2. 启用并保存

## 🎯 下一步

修复完成后，重新运行：
```bash
python diagnose_nas.py
```

如果SSH连接成功，就可以运行主程序了：
```bash
python main.py
``` 