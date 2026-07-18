#!/bin/bash
set -e

echo "🚀 Установка дополнительной VPN-ноды"

# Установка Docker (если не установлен)
if ! command -v docker &> /dev/null; then
    echo "🐳 Установка Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm get-docker.sh
fi

read -p "Введите публичный IP адрес (или домен) МАСТЕР-сервера (например, http://1.2.3.4:8000): " ADMIN_API_URL
read -p "Введите ADMIN_API_KEY (выдавался при установке мастер-сервера): " ADMIN_API_KEY
read -p "Введите REALITY_PRIVATE_KEY мастер-сервера: " REALITY_PRIVATE_KEY
read -p "Введите REALITY_SHORT_ID мастер-сервера: " REALITY_SHORT_ID
read -p "Введите публичный IP адрес ЭТОЙ новой ноды: " NODE_IP

cat <<EOF_DOCKER > docker-compose-node.yml
version: '3.8'

services:
  node_server:
    build:
      context: ./node_server
      dockerfile: Dockerfile
    restart: always
    environment:
      - ADMIN_API_URL=$ADMIN_API_URL
      - ADMIN_API_KEY=$ADMIN_API_KEY
      - NODE_IP=$NODE_IP
      - XRAY_API_PORT=10085
      - REALITY_PRIVATE_KEY=$REALITY_PRIVATE_KEY
      - REALITY_SHORT_ID=$REALITY_SHORT_ID
    ports:
      - "443:443"
      - "80:80"
    network_mode: "host"
EOF_DOCKER

echo "⚙️ Запускаем контейнер ноды..."
# Build the node image using the standalone compose file
sudo docker compose -f docker-compose-node.yml up -d --build

echo "🎉 Дополнительная нода успешно установлена и запущена!"
echo "Не забудьте добавить этот сервер через админ-панель бота: /addnode $NODE_IP 443"
