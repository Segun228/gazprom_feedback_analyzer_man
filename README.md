# Feedback Analyzer Platform

## 📌 Описание

Проект представляет собой платформу с **API Gateway**, интеграцией с **Kafka** и **ClickHouse**.  
Система развертывается с помощью `docker-compose` и предназначена для обработки и хранения отзывов.

## 🏗️ Архитектура (на текущий момент)

- **API Gateway** — точка входа для запросов (Go, Chi).
- **ClickHouse** — аналитическая СУБД.
- **Kafka + Zookeeper** — брокер сообщений для обмена событиями между сервисами.
- **Kafdrop** — веб-интерфейс для работы с Kafka.

## 🚀 Запуск

1. Клонировать репозиторий:

   ```bash
   git clone  https://github.com/Segun228/gazprom_feedback_analyzer_man
   cd gazprom_feedback_analyzer_man
   ```

1. Создать файл `.env` в корне проекта и заполнить в соответствии с `.env.example`

1. Запустить сервисы:

    ```bash
    docker-compose up --build
    ```

1. Проверить, что все поднялось:

   - API Gateway: [http://localhost:3000]
   - ClickHouse (HTTP): [http://localhost:8123]
   - Kafka (локальный доступ): [localhost:29092]
   - Kafdrop: [http://localhost:19000]

## 🗂️ Структура проекта

```markdown
.
├── api-gateway/        # исходный код API Gateway (Go)
│   ├── config.yaml     # конфигурация
│   └── ...
├── docker-compose.yml  # сервисы платформы
└── README.md           # документация
```

## 🌐 Порты

| Сервис      | Занимаемый(-ые) порт(-ы) | Назначение                          |
| ----------- | ------------------------ | ----------------------------------- |
| API Gateway | `3000`                   | HTTP API                            |
| ClickHouse  | `8123`                   | HTTP интерфейс (REST/SQL)           |
|             | `9000`                   | TCP интерфейс (native client)       |
|             | `9009`                   | Протокол взаимодействия (optional)  |
| Zookeeper   | `2181`                   | Клиентские подключения              |
| Kafka       | `9092`                   | Внутренние подключения (контейнеры) |
|             | `29092`                  | Подключение с хоста (localhost)     |
| Kafdrop     | `19000`                  | Веб-интерфейс для Kafka             |

## 🛠️ Полезные команды

- ClickHouse CLI:

```bash
   docker exec -it clickhouse clickhouse-client -u user --password password
```

- Логи API Gateway:

```bash
docker logs -f api-gateway
```

- Список топиков Kafka:

```bash
docker exec -it kafka kafka-topics --bootstrap-server localhost:9092 --list
```
