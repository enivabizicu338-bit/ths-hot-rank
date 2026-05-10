# 同花顺热榜系统 - 腾讯云部署指南

## 一、服务器准备

### 1.1 购买腾讯云服务器
- 推荐配置：2核4G内存，50G硬盘
- 操作系统：Ubuntu 22.04 LTS（推荐）或 CentOS 8
- 安全组开放端口：22(SSH)、80(HTTP)、443(HTTPS)

### 1.2 连接服务器
```bash
ssh root@你的服务器IP
```

## 二、快速部署（一键脚本）

### 方式一：自动安装脚本
```bash
# 下载并执行安装脚本
curl -fsSL https://raw.githubusercontent.com/enivabizicu338-bit/ths-hot-rank/main/deploy/install.sh | bash
```

### 方式二：手动部署
```bash
# 1. 更新系统
apt update && apt upgrade -y

# 2. 安装依赖
apt install -y git python3 python3-pip python3-venv nginx supervisor

# 3. 克隆代码
cd /opt
git clone https://github.com/enivabizicu338-bit/ths-hot-rank.git
cd ths-hot-rank

# 4. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 5. 安装Python依赖
pip install -r requirements.txt
pip install gunicorn

# 6. 启动服务
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 三、Docker部署（推荐）

### 3.1 安装Docker
```bash
curl -fsSL https://get.docker.com | bash
systemctl start docker
systemctl enable docker
```

### 3.2 部署应用
```bash
cd /opt
git clone https://github.com/enivabizicu338-bit/ths-hot-rank.git
cd ths-hot-rank

# 构建并启动
docker-compose up -d --build
```

### 3.3 查看日志
```bash
docker-compose logs -f
```

## 四、配置域名（可选）

### 4.1 域名解析
在腾讯云DNS解析中添加A记录，指向服务器IP

### 4.2 配置Nginx
```bash
# 编辑Nginx配置
nano /etc/nginx/sites-available/ths-hot-rank

# 修改 server_name _ 为你的域名
server_name your-domain.com;

# 重启Nginx
nginx -t && systemctl restart nginx
```

### 4.3 配置HTTPS（免费SSL）
```bash
# 安装Certbot
apt install -y certbot python3-certbot-nginx

# 获取SSL证书
certbot --nginx -d your-domain.com

# 自动续期
certbot renew --dry-run
```

## 五、常用命令

### 服务管理
```bash
# 查看状态
supervisorctl status ths-hot-rank

# 重启服务
supervisorctl restart ths-hot-rank

# 查看日志
tail -f /var/log/ths-hot-rank.log
```

### Docker管理
```bash
# 查看容器状态
docker-compose ps

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f

# 更新代码
git pull && docker-compose up -d --build
```

## 六、安全配置

### 6.1 防火墙设置
```bash
# Ubuntu UFW
ufw allow 22
ufw allow 80
ufw allow 443
ufw enable

# CentOS Firewalld
firewall-cmd --permanent --add-port=22/tcp
firewall-cmd --permanent --add-port=80/tcp
firewall-cmd --permanent --add-port=443/tcp
firewall-cmd --reload
```

### 6.2 定时同步数据（可选）
```bash
# 添加定时任务
crontab -e

# 每5分钟同步一次数据
*/5 * * * * cd /opt/ths-hot-rank && /opt/ths-hot-rank/venv/bin/python scripts/sync_data.py
```

## 七、故障排查

### 服务无法启动
```bash
# 检查端口占用
netstat -tlnp | grep 5000

# 检查日志
tail -100 /var/log/ths-hot-rank.log
```

### 数据同步失败
```bash
# 手动同步
cd /opt/ths-hot-rank
source venv/bin/activate
python scripts/sync_data.py
```

---

**部署完成后访问**: http://你的服务器IP