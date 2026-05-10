#!/bin/bash
# 同花顺热榜系统 - 腾讯云部署脚本
# 适用于 Ubuntu 20.04/22.04 或 CentOS 7/8

set -e

echo "=========================================="
echo "  同花顺热榜系统 - 腾讯云部署脚本"
echo "=========================================="

# 检测操作系统
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VER=$VERSION_ID
else
    echo "无法检测操作系统"
    exit 1
fi

echo "检测到操作系统: $OS $VER"

# 更新系统
echo "[1/6] 更新系统包..."
if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
    apt update && apt upgrade -y
    apt install -y git python3 python3-pip python3-venv nginx supervisor
elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ]; then
    yum update -y
    yum install -y git python3 python3-pip nginx supervisor
fi

# 创建应用目录
echo "[2/6] 创建应用目录..."
APP_DIR="/opt/ths-hot-rank"
mkdir -p $APP_DIR
cd $APP_DIR

# 克隆代码
if [ ! -d "$APP_DIR/.git" ]; then
    REPO_URL="https://github.com/enivabizicu338-bit/ths-hot-rank.git"
    git clone $REPO_URL .
fi

# 创建虚拟环境
echo "[3/6] 创建Python虚拟环境..."
python3 -m venv venv
source venv/bin/activate

# 安装依赖
echo "[4/6] 安装Python依赖..."
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# 创建数据目录
mkdir -p data

# 配置 Supervisor
echo "[6/6] 配置系统服务..."
cat > /etc/supervisor/conf.d/ths-hot-rank.conf << 'SUPERVISOR_EOF'
[program:ths-hot-rank]
directory=/opt/ths-hot-rank
command=/opt/ths-hot-rank/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app
user=root
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=60
redirect_stderr=true
stdout_logfile=/var/log/ths-hot-rank.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10
SUPERVISOR_EOF

# 配置 Nginx
cat > /etc/nginx/sites-available/ths-hot-rank << 'NGINX_EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /static {
        alias /opt/ths-hot-rank/static;
        expires 30d;
    }
}
NGINX_EOF

# 启用站点
ln -sf /etc/nginx/sites-available/ths-hot-rank /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# 重启服务
supervisorctl reread
supervisorctl update
supervisorctl restart ths-hot-rank
nginx -t && systemctl restart nginx

echo "部署完成！"