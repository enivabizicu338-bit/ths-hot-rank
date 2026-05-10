#!/bin/bash
# 同花顺热榜系统 - 快速部署脚本（单行命令版）
# 用法: sudo bash install.sh [版本号] [端口]
# 示例: sudo bash install.sh v1 5000

set -e
VERSION=${1:-v1}
PORT=${2:-5000}
APP_DIR="/opt/projects/ths-hot-rank-${VERSION}"
REPO_URL="https://github.com/enivabizicu338-bit/ths-hot-rank.git"

echo "=========================================="
echo "  同花顺热榜系统 - 部署 ${VERSION} (端口:${PORT})"
echo "=========================================="

if [ "$EUID" -ne 0 ]; then
    echo "请使用 sudo 执行！"
    exit 1
fi

echo "[1/4] 安装Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | bash
    systemctl start docker && systemctl enable docker
fi

echo "[2/4] 克隆代码到 ${APP_DIR}..."
mkdir -p /opt/projects
if [ ! -d "${APP_DIR}/.git" ]; then
    git clone ${REPO_URL} ${APP_DIR}
else
    cd ${APP_DIR} && git pull
fi

cd ${APP_DIR}
mkdir -p data

echo "[3/4] 配置端口 ${PORT}..."
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

echo "[4/4] 启动Docker..."
docker compose up -d --build
sleep 3

echo ""
echo "=========================================="
echo "  部署完成！"
echo "=========================================="
echo "  版本: ${VERSION} | 端口: ${PORT}"
echo "  访问: http://$(curl -s ifconfig.me):${PORT}"
echo ""
echo "常用命令:"
echo "  日志: cd ${APP_DIR} && docker compose logs -f"
echo "  重启: cd ${APP_DIR} && docker compose restart"
echo "  停止: cd ${APP_DIR} && docker compose down"
echo ""
echo "部署第二套: sudo bash install.sh v2 5001"