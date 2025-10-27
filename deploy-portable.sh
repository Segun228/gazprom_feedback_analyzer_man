#!/bin/bash
# deploy-portable.sh - Портабельное развертывание со встроенным SSH ключом

set -e

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                🚀 GAZPROM FEEDBACK ANALYZER 🚀                 ║"
echo "║              Портабельное развертывание с Serveo                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Установка встроенного SSH ключа
setup_ssh_key() {
    local ssh_key_path="$HOME/.ssh/serveo_embedded_key"
    
    echo "🔑 Установка встроенного SSH ключа..."
    mkdir -p "$HOME/.ssh"
    
    # Встроенный приватный ключ
    cat > "$ssh_key_path" << 'EOF'
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACBao1a16e7qz5x6aOZFQl5zsp5dX5pRPb1ryQ0SWN1VAQAAAJgKWYHjClmB
4wAAAAtzc2gtZWQyNTUxOQAAACBao1a16e7qz5x6aOZFQl5zsp5dX5pRPb1ryQ0SWN1VAQ
AAAED2ZxOeimYCj5QRdRmOhz8NpLjUJdD3p/OWBKpOaHT7xlqjVrXp7urPnHpo5kVCXnOy
nl1fmlE9vWvJDRJY3VUBAAAAFm1hYy1nYXpwcm9tLXNlcnZlbw==
-----END OPENSSH PRIVATE KEY-----
EOF

    # Встроенный публичный ключ
    cat > "${ssh_key_path}.pub" << 'EOF'
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFqjVrXp7urPnHpo5kVCXnOynl1fmlE9vWvJDRJY3VUB mac-gazprom-serveo
EOF

    chmod 600 "$ssh_key_path"
    chmod 644 "${ssh_key_path}.pub"
    
    echo "✅ SSH ключ установлен: $ssh_key_path"
}

# Проверка зависимостей
check_dependencies() {
    echo "📋 Проверка системных требований..."
    
    local missing_deps=()
    
    if ! command -v docker &> /dev/null; then
        missing_deps+=("Docker")
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        missing_deps+=("Docker Compose")
    fi
    
    if ! command -v ssh &> /dev/null; then
        missing_deps+=("SSH")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        echo "❌ Не найдены зависимости: ${missing_deps[*]}"
        echo "Установите их и запустите скрипт снова."
        exit 1
    fi
    
    echo "✅ Все зависимости найдены!"
}

# Функция очистки при завершении
cleanup() {
    echo ""
    echo "🛑 Остановка сервисов..."
    
    # Остановка Serveo туннеля
    if [ ! -z "$SERVEO_PID" ] && kill -0 "$SERVEO_PID" 2>/dev/null; then
        kill "$SERVEO_PID" 2>/dev/null || true
    fi
    
    # Остановка Docker контейнеров
    docker-compose down 2>/dev/null || true
    
    echo "✅ Все сервисы остановлены."
}

# Запуск Serveo туннеля
start_serveo_tunnel() {
    local tunnel_subdomain="gazprom-analyzer-mac2024"
    local local_port="3000"
    local ssh_key_path="$HOME/.ssh/serveo_embedded_key"
    
    echo "🌐 Запуск Serveo туннеля на домен: ${tunnel_subdomain}.serveo.net"
    
    # Запуск туннеля в фоновом режиме
    (
        while true; do
            echo "$(date): Подключение к ${tunnel_subdomain}.serveo.net..."
            
            ssh -i "$ssh_key_path" \
                -o StrictHostKeyChecking=no \
                -o ServerAliveInterval=60 \
                -o ServerAliveCountMax=3 \
                -o ConnectTimeout=30 \
                -o ExitOnForwardFailure=yes \
                -R ${tunnel_subdomain}.serveo.net:80:localhost:${local_port} \
                serveo.net
            
            echo "$(date): Соединение разорвано. Переподключение через 10 сек..."
            sleep 10
        done
    ) &
    
    SERVEO_PID=$!
    echo "✅ Serveo туннель запущен (PID: $SERVEO_PID)"
    echo "🌍 Публичный URL: https://${tunnel_subdomain}.serveo.net"
}

# Установка обработчика сигналов
trap cleanup SIGINT SIGTERM EXIT

# Основная логика
main() {
    check_dependencies
    setup_ssh_key
    
    echo "🔄 Остановка существующих контейнеров..."
    docker-compose down --remove-orphans 2>/dev/null || true
    
    read -p "🧹 Очистить Docker кэш и volumes? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️ Очистка Docker..."
        docker system prune -f --volumes
    fi
    
    echo "🚀 Запуск Docker контейнеров..."
    docker-compose up -d
    
    echo "⏳ Ожидание запуска сервисов..."
    sleep 15
    
    # Проверка статуса контейнеров
    echo "📊 Статус контейнеров:"
    docker-compose ps
    
    # Запуск Serveo туннеля
    start_serveo_tunnel
    
    echo ""
    echo "🎉 Развертывание завершено!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🌍 Публичный URL: https://gazprom-feedback-test.serveo.net"
    echo "🏠 API Gateway:   http://localhost:3000"
    echo "📊 Grafana:       http://localhost:3001 (admin/admin123)"
    echo "🔍 Kafka UI:      http://localhost:8080"
    echo "🗄️ ClickHouse:    http://localhost:8123"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "🛠️ Управление:"
    echo "   docker-compose logs -f    # Просмотр логов"
    echo "   docker-compose down       # Остановка"
    echo "   docker-compose restart    # Перезапуск"
    echo ""
    echo "Нажмите Ctrl+C для остановки..."
    
    # Ожидание завершения
    wait "$SERVEO_PID" 2>/dev/null || true
}

main "$@"