# Grafana Auto-Provisioning

Автоматическая генерация конфигурации Grafana из шаблонов при каждом запуске.

## Как это работает

При запуске контейнера `entrypoint.sh` генерирует файлы из `*.template` с подстановкой переменных из `.env`:

- `clickhouse.yml.template` → `clickhouse.yml` (datasource)
- `dashboard.json.template` → `dashboard.json` (дашборды)

## Переменные

Из `.env` подставляются:

- `$CLICKHOUSE_DB` - имя базы данных
- `$CLICKHOUSE_USER` - пользователь
- `$CLICKHOUSE_PASSWORD` - пароль

## Изменение дашбордов

1. Внесите изменения через Grafana UI
2. Экспортируйте: Share → Export → Save JSON
3. Замените `dashboards/dashboard.json.template`
4. Замените имена БД на переменную:

   ```bash
   sed -i 's/FROM db\./FROM $CLICKHOUSE_DB./g' dashboard.json.template
   ```

## Git

✅ **Коммитим:** `*.template`, `entrypoint.sh`  
❌ **Не коммитим:** сгенерированные `.yml` и `.json` (в `.gitignore`)
