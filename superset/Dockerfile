FROM apache/superset:latest

# Переключаемся на root для установки пакетов
USER root

# Устанавливаем драйвер ClickHouse
RUN pip install clickhouse-connect

# Возвращаемся к пользователю superset
USER superset