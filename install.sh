#!/bin/bash
set -e

echo "🚀 Начинаем установку VPN-сервиса"
echo "Выберите тип установки:"
echo "1) Установить всё вместе (Мастер-сервер + Нода)"
echo "2) Установить только Мастер-сервер (Админ-панель + БД, без VPN-ноды)"
echo "3) Установить только дополнительную VPN-ноду"
read -p "Введите номер (1, 2 или 3): " INSTALL_TYPE

# Обновление и установка зависимостей
echo "📦 Установка зависимостей..."
sudo apt-get update
sudo apt-get install -y curl git openssl unzip

# Настройка UFW (Firewall)
echo "🛡️ Настройка брандмауэра (UFW)..."
sudo apt-get install -y ufw
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

if [ "$INSTALL_TYPE" = "1" ] || [ "$INSTALL_TYPE" = "2" ]; then
    # Мастер-серверу нужен открытый порт 8000 для API
    sudo ufw allow 8000/tcp
fi
sudo ufw --force enable

# Установка Docker и Docker Compose (если не установлены)
if ! command -v docker &> /dev/null; then
    echo "🐳 Установка Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm get-docker.sh
fi

if [ "$INSTALL_TYPE" = "1" ] || [ "$INSTALL_TYPE" = "2" ]; then
    echo "🔑 Настройка конфигурации Мастер-сервера..."
    ADMIN_API_KEY=$(openssl rand -hex 32)
    POSTGRES_PASSWORD=$(openssl rand -hex 16)
    REDIS_PASSWORD=$(openssl rand -hex 16)

    # Generate valid x25519 keys for Reality
    XRAY_VERSION="v1.8.24"
    XRAY_SHA256="47a860787e823474a358d6bca536547df6dd08b69c6de482ea92a9e7e8f8969c"
    curl -sL https://github.com/XTLS/Xray-core/releases/download/${XRAY_VERSION}/Xray-linux-64.zip -o xray.zip

    if ! echo "$XRAY_SHA256  xray.zip" | sha256sum -c -; then
        echo "❌ Ошибка: Несовпадение контрольной суммы Xray-core!"
        exit 1
    fi

    unzip -q xray.zip xray -d /tmp/
    chmod +x /tmp/xray
    REALITY_KEYS=$(/tmp/xray x25519)
    REALITY_PRIVATE_KEY=$(echo "$REALITY_KEYS" | grep "Private key" | awk '{print $3}')
    REALITY_PUBLIC_KEY=$(echo "$REALITY_KEYS" | grep "Public key" | awk '{print $3}')
    REALITY_SHORT_ID=$(openssl rand -hex 8)
    rm -f /tmp/xray xray.zip

    # Запрашиваем данные у администратора
    read -p "Введите токен вашего Telegram-бота (@BotFather): " BOT_TOKEN
    read -p "Введите ваш Telegram ID (чтобы получить права админа): " ADMIN_IDS
    read -p "Введите токен от CryptoBot (для пополнения криптой, если нет - нажмите Enter): " CRYPTO_PAY_TOKEN
    read -p "Введите IP адрес текущего сервера (публичный): " NODE_IP

    if [ -z "$CRYPTO_PAY_TOKEN" ]; then
        CRYPTO_PAY_TOKEN="mock_token"
    fi

    if [ -f .env ]; then
        echo "⚠️ Файл .env уже существует. Использование текущих ключей, чтобы не прервать работу существующих нод."
        source .env
    else
        # Создаем .env файл
        cat <<ENV_EOF > .env
BOT_TOKEN=$BOT_TOKEN
ADMIN_IDS=$ADMIN_IDS
CRYPTO_PAY_TOKEN=$CRYPTO_PAY_TOKEN
ADMIN_API_KEY=$ADMIN_API_KEY
NODE_IP=$NODE_IP
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
REDIS_PASSWORD=$REDIS_PASSWORD
DATABASE_URL=postgresql+asyncpg://vpn_admin:$POSTGRES_PASSWORD@db:5432/vpn_db
REALITY_PRIVATE_KEY=$REALITY_PRIVATE_KEY
REALITY_PUBLIC_KEY=$REALITY_PUBLIC_KEY
REALITY_SHORT_ID=$REALITY_SHORT_ID
ENV_EOF
        chmod 600 .env
        echo "✅ Конфигурация сохранена в .env"
    fi

    if [ "$INSTALL_TYPE" = "1" ]; then
        echo "⚙️ Настройка Docker Compose для Мастер-сервера + Ноды..."
        cat <<EOF_DOCKER > docker-compose.yml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    restart: always
    environment:
      POSTGRES_USER: vpn_admin
      POSTGRES_PASSWORD: \${POSTGRES_PASSWORD:-vpn_password}
      POSTGRES_DB: vpn_db
    volumes:
      - db_data:/var/lib/postgresql/data
    networks:
      - vpn_network

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass \${REDIS_PASSWORD:-vpn_redis_pass}
    restart: always
    volumes:
      - redis_data:/data
    networks:
      - vpn_network

  admin_server:
    build:
      context: ./admin_server
      dockerfile: Dockerfile
    restart: always
    environment:
      - DATABASE_URL=\${DATABASE_URL:-postgresql+asyncpg://vpn_admin:vpn_password@db:5432/vpn_db}
      - REDIS_URL=redis://:\${REDIS_PASSWORD:-vpn_redis_pass}@redis:6379/0
      - BOT_TOKEN=\${BOT_TOKEN}
      - ADMIN_IDS=\${ADMIN_IDS}
      - CRYPTO_PAY_TOKEN=\${CRYPTO_PAY_TOKEN}
      - ADMIN_API_KEY=\${ADMIN_API_KEY}
      - API_DOMAIN=http://\${NODE_IP:-127.0.0.1}:8000
      - REALITY_PUBLIC_KEY=\${REALITY_PUBLIC_KEY}
      - REALITY_SHORT_ID=\${REALITY_SHORT_ID}
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis
    networks:
      - vpn_network

  node_server:
    build:
      context: ./node_server
      dockerfile: Dockerfile
    restart: always
    environment:
      - ADMIN_API_URL=http://admin_server:8000
      - ADMIN_API_KEY=\${ADMIN_API_KEY}
      - API_DOMAIN=http://\${NODE_IP:-127.0.0.1}:8000
      - REALITY_PUBLIC_KEY=\${REALITY_PUBLIC_KEY}
      - REALITY_SHORT_ID=\${REALITY_SHORT_ID}
      - XRAY_API_PORT=10085
      - NODE_IP=\${NODE_IP:-127.0.0.1}
      - REALITY_PRIVATE_KEY=\${REALITY_PRIVATE_KEY}
    ports:
      - "443:443"     # Reality port
      - "80:80"       # Optional HTTP port
    depends_on:
      - admin_server
    networks:
      - vpn_network

volumes:
  db_data:
  redis_data:

networks:
  vpn_network:
    driver: bridge
EOF_DOCKER
    elif [ "$INSTALL_TYPE" = "2" ]; then
        echo "⚙️ Настройка Docker Compose для Мастер-сервера (без Ноды)..."
        cat <<EOF_DOCKER > docker-compose.yml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    restart: always
    environment:
      POSTGRES_USER: vpn_admin
      POSTGRES_PASSWORD: \${POSTGRES_PASSWORD:-vpn_password}
      POSTGRES_DB: vpn_db
    volumes:
      - db_data:/var/lib/postgresql/data
    networks:
      - vpn_network

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass \${REDIS_PASSWORD:-vpn_redis_pass}
    restart: always
    volumes:
      - redis_data:/data
    networks:
      - vpn_network

  admin_server:
    build:
      context: ./admin_server
      dockerfile: Dockerfile
    restart: always
    environment:
      - DATABASE_URL=\${DATABASE_URL:-postgresql+asyncpg://vpn_admin:vpn_password@db:5432/vpn_db}
      - REDIS_URL=redis://:\${REDIS_PASSWORD:-vpn_redis_pass}@redis:6379/0
      - BOT_TOKEN=\${BOT_TOKEN}
      - ADMIN_IDS=\${ADMIN_IDS}
      - CRYPTO_PAY_TOKEN=\${CRYPTO_PAY_TOKEN}
      - ADMIN_API_KEY=\${ADMIN_API_KEY}
      - API_DOMAIN=http://\${NODE_IP:-127.0.0.1}:8000
      - REALITY_PUBLIC_KEY=\${REALITY_PUBLIC_KEY}
      - REALITY_SHORT_ID=\${REALITY_SHORT_ID}
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis
    networks:
      - vpn_network

volumes:
  db_data:
  redis_data:

networks:
  vpn_network:
    driver: bridge
EOF_DOCKER
        echo "🧹 Удаление файлов ноды (так как выбрана только админ-панель)..."
        rm -rf node_server
    fi

    echo "⚙️ Запускаем контейнеры (это займет несколько минут при первой сборке)..."
    sudo docker compose up -d --build

    echo "🎉 Установка завершена!"
    echo "Бот должен быть активен. Напишите ему /start, затем /admin для управления."
    echo "Внимание: Сохраните эти данные для подключения будущих нод:"
    echo "ADMIN_API_KEY=$ADMIN_API_KEY"
    echo "REALITY_PRIVATE_KEY=$REALITY_PRIVATE_KEY"
    echo "REALITY_SHORT_ID=$REALITY_SHORT_ID"
    if [ "$INSTALL_TYPE" = "1" ]; then
        echo "Не забудьте добавить эту ноду в боте через: /addnode $NODE_IP 443"
    fi

elif [ "$INSTALL_TYPE" = "3" ]; then
    echo "⚙️ Настройка конфигурации дополнительной VPN-ноды..."
    read -p "Введите публичный IP адрес (или домен) МАСТЕР-сервера (например, http://1.2.3.4:8000): " ADMIN_API_URL
    read -p "Введите ADMIN_API_KEY (выдавался при установке мастер-сервера): " ADMIN_API_KEY
    read -p "Введите REALITY_PRIVATE_KEY мастер-сервера: " REALITY_PRIVATE_KEY
    read -p "Введите REALITY_SHORT_ID мастер-сервера: " REALITY_SHORT_ID
    read -p "Введите публичный IP адрес ЭТОЙ новой ноды: " NODE_IP

    cat <<EOF_DOCKER > docker-compose.yml
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
EOF_DOCKER

    echo "🧹 Удаление файлов админ-панели (так как выбрана только нода)..."
    rm -rf admin_server

    echo "⚙️ Запускаем контейнер ноды..."
    sudo docker compose up -d --build

    echo "🎉 Дополнительная нода успешно установлена и запущена!"
    echo "Не забудьте добавить этот сервер через админ-панель бота: /addnode $NODE_IP 443"
else
    echo "❌ Неверный выбор. Пожалуйста, запустите скрипт заново и выберите 1, 2 или 3."
    exit 1
fi
