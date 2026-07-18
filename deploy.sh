#!/bin/bash
set -e

echo "🚀 Начинаем установку VPN Master Server (Admin + БД + Node)"

# Обновление и установка зависимостей
echo "📦 Установка зависимостей..."
sudo apt-get update
sudo apt-get install -y curl git openssl

# Установка Docker и Docker Compose (если не установлены)
if ! command -v docker &> /dev/null; then
    echo "🐳 Установка Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm get-docker.sh
fi

# Генерация ключей
echo "🔑 Настройка конфигурации..."
ADMIN_API_KEY=$(openssl rand -hex 32)
POSTGRES_PASSWORD=$(openssl rand -hex 16)

# Generate valid x25519 keys for Reality
curl -sL https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip -o xray.zip
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

# Создаем .env файл
cat <<ENV_EOF > .env
BOT_TOKEN=$BOT_TOKEN
ADMIN_IDS=$ADMIN_IDS
CRYPTO_PAY_TOKEN=$CRYPTO_PAY_TOKEN
ADMIN_API_KEY=$ADMIN_API_KEY
NODE_IP=$NODE_IP
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
DATABASE_URL=postgresql+asyncpg://vpn_admin:$POSTGRES_PASSWORD@db:5432/vpn_db
REALITY_PRIVATE_KEY=$REALITY_PRIVATE_KEY
REALITY_PUBLIC_KEY=$REALITY_PUBLIC_KEY
REALITY_SHORT_ID=$REALITY_SHORT_ID
ENV_EOF

echo "✅ Конфигурация сохранена в .env"

# Запуск
echo "⚙️ Запускаем контейнеры (это займет несколько минут при первой сборке)..."
sudo docker compose up -d --build

echo "🎉 Установка завершена!"
echo "Бот должен быть активен. Напишите ему /start, затем /admin для управления."
echo "Внимание: Сохраните эти данные для подключения будущих нод:"
echo "ADMIN_API_KEY=$ADMIN_API_KEY"
echo "REALITY_PRIVATE_KEY=$REALITY_PRIVATE_KEY"
echo "REALITY_SHORT_ID=$REALITY_SHORT_ID"
