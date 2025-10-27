#!/bin/bash
# serveo-tunnel-portable.sh - Портабельный туннель со встроенным SSH ключом

TUNNEL_SUBDOMAIN="gazprom-analyzer-mac2024"  # Уникальный домен
LOCAL_PORT="3000"                         # Порт вашего приложения
SSH_KEY_PATH="$HOME/.ssh/serveo_embedded_key"
MAX_RETRIES=2000                          # Максимальное количество попыток
RETRY_DELAY=10                            # Пауза между переподключениями

echo "🔑 Настройка портабельного Serveo туннеля..."
echo "🌐 Домен: https://${TUNNEL_SUBDOMAIN}.serveo.net"
echo "💻 Локальный порт: ${LOCAL_PORT}"
echo "🔐 Встроенный SSH ключ"
echo "----------------------------------------"

# Создаем директорию для SSH ключей если её нет
mkdir -p "$HOME/.ssh"

# Встроенный приватный ключ
cat > "$SSH_KEY_PATH" << 'EOF'
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACBao1a16e7qz5x6aOZFQl5zsp5dX5pRPb1ryQ0SWN1VAQAAAJgKWYHjClmB
4wAAAAtzc2gtZWQyNTUxOQAAACBao1a16e7qz5x6aOZFQl5zsp5dX5pRPb1ryQ0SWN1VAQ
AAAED2ZxOeimYCj5QRdRmOhz8NpLjUJdD3p/OWBKpOaHT7xlqjVrXp7urPnHpo5kVCXnOy
nl1fmlE9vWvJDRJY3VUBAAAAFm1hYy1nYXpwcm9tLXNlcnZlbw==
-----END OPENSSH PRIVATE KEY-----
EOF

# Встроенный публичный ключ
cat > "${SSH_KEY_PATH}.pub" << 'EOF'
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFqjVrXp7urPnHpo5kVCXnOynl1fmlE9vWvJDRJY3VUB mac-gazprom-serveo
EOF

# Устанавливаем правильные права доступа
chmod 600 "$SSH_KEY_PATH"
chmod 644 "${SSH_KEY_PATH}.pub"

echo "✅ SSH ключи установлены в: $SSH_KEY_PATH"

COUNTER=0

while [ $COUNTER -lt $MAX_RETRIES ]; do
    echo "$(date): Подключение #$((COUNTER+1)) к ${TUNNEL_SUBDOMAIN}.serveo.net..."
    
    # Запускаем туннель с встроенным SSH ключом
    ssh -i "$SSH_KEY_PATH" \
        -o StrictHostKeyChecking=no \
        -o ServerAliveInterval=60 \
        -o ServerAliveCountMax=3 \
        -o ConnectTimeout=30 \
        -o ExitOnForwardFailure=yes \
        -R ${TUNNEL_SUBDOMAIN}.serveo.net:80:localhost:${LOCAL_PORT} \
        serveo.net
    
    EXIT_CODE=$?
    
    echo "$(date): Соединение разорвано. Переподключение через ${RETRY_DELAY} сек..."
    sleep $RETRY_DELAY
    COUNTER=$((COUNTER+1))
done

echo "❌ Достигнуто максимальное количество попыток."