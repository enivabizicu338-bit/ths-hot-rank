#!/bin/bash
# ============================================
#  同花顺热榜系统 - 多版本部署脚本
#  用法: sudo ./deploy.sh [版本号] [端口]
#  示例: sudo ./deploy.sh v1 5000
#        sudo ./deploy.sh v2 5001
# ============================================

set -e

VERSION=${1:-v1}
PORT=${2:-5000}
APP_NAME="ths-hot-rank-${VERSION}"
APP_DIR="/opt/projects/${APP_NAME}"
REPO_URL="https://github.com/enivabizicu338-bit/ths-hot-rank.git"

echo "=========================================="
echo "  同花顺热榜系统 - 部署 ${VERSION}"
echo "  端口: ${PORT}"
echo "  目录: ${APP_DIR}"
echo "=========================================="

# 检查root权限
if [ "$EUID" -ne 0 ]; then
    echo "错误: 请使用 sudo 执行此脚本"
    echo "  sudo bash deploy.sh ${VERSION} ${PORT}"
    exit 1
fi

# 检测操作系统
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "无法检测操作系统"
    exit 1
fi
echo "检测到操作系统: $OS ${VERSION_ID}"

# 安装Docker
echo "[1/5] 检查Docker..."
if ! command -v docker &> /dev/null; then
    echo "安装Docker..."
    curl -fsSL https://get.docker.com | bash
    systemctl start docker
    systemctl enable docker
else
    echo "Docker已安装: $(docker --version)"
fi

# 检查docker-compose
if ! docker compose version &> /dev/null; then
    echo "安装docker-compose..."
    apt-get install -y docker-compose-plugin 2>/dev/null || pip3 install docker-compose
fi

# 创建项目目录
echo "[2/5] 创建项目目录: ${APP_DIR}"
mkdir -p /opt/projects
mkdir -p ${APP_DIR}

# 克隆代码
echo "[3/5] 克隆代码..."
if [ ! -d "${APP_DIR}/.git" ]; then
    git clone ${REPO_URL} ${APP_DIR}
else
    cd ${APP_DIR}
    git pull
fi

cd ${APP_DIR}
mkdir -p data

# 生成端口配置
echo "[4/5] 配置Docker（端口: ${PORT}）..."
cat > docker-compose.override.yml << EOF
version: '3.8'
services:
  web:
    ports:
      - "${PORT}:5000"
    restart: unless-stopped
    environment:
      - FLASK_ENV=production
      - APP_VERSION=${VERSION}
  nginx:
    profiles:
      - without-nginx
EOF

# 启动服务
echo "[5/5] 启动服务..."
docker compose up -d --build

sleep 5

echo ""
echo "=========================================="
echo "  部署完成！"
echo "=========================================="
echo "  版本: ${VERSION}"
echo "  目录: ${APP_DIR}"
echo "  访问: http://$(curl -s ifconfig.me):${PORT}"
echo ""
echo "常用命令:"
echo "  状态: cd ${APP_DIR} && docker compose ps"
echo "  日志: cd ${APP_DIR} && docker compose logs -f"
echo "  重启: cd ${APP_DIR} && docker compose restart"
echo "  停止: cd ${APP_DIR} && docker compose down"
echo ""
echo "部署更多版本:"
echo "  sudo bash deploy.sh v2 5001"
echo "  sudo bash deploy.sh v3 5002"