#!/bin/sh
# Подставляем переменные окружения в provisioning файлы перед запуском Grafana

set -e

echo "=== Grafana Provisioning: Substituting environment variables ==="

# Создаем все необходимые директории для provisioning
mkdir -p /tmp/grafana-provisioning/datasources
mkdir -p /tmp/grafana-provisioning/dashboards
mkdir -p /tmp/grafana-provisioning/plugins
mkdir -p /tmp/grafana-provisioning/notifiers
mkdir -p /tmp/grafana-provisioning/alerting

# Генерируем datasource конфиг из шаблона
if [ -f /etc/grafana/provisioning/datasources/clickhouse.yml.template ]; then
    sed "s/\$CLICKHOUSE_DB/${CLICKHOUSE_DB}/g; s/\$CLICKHOUSE_USER/${CLICKHOUSE_USER}/g; s/\$CLICKHOUSE_PASSWORD/${CLICKHOUSE_PASSWORD}/g" \
        /etc/grafana/provisioning/datasources/clickhouse.yml.template \
        > /tmp/grafana-provisioning/datasources/clickhouse.yml
    echo "[OK] Datasource config generated: DB=${CLICKHOUSE_DB}, USER=${CLICKHOUSE_USER}"
fi

# Генерируем dashboards из шаблонов
for template in /var/lib/grafana/dashboards/*.json.template; do
    if [ -f "$template" ]; then
        dashboard="/tmp/grafana-provisioning/dashboards/$(basename ${template%.template})"
        sed "s/\$CLICKHOUSE_DB/${CLICKHOUSE_DB}/g" "$template" > "$dashboard"
        echo "[OK] Dashboard generated: $(basename $dashboard)"
    fi
done

# Создаем конфиг provisioning для dashboards
cat > /tmp/grafana-provisioning/dashboards.yml <<EOF
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /tmp/grafana-provisioning/dashboards
EOF

echo "=== Provisioning complete! Starting Grafana ==="

# Запускаем оригинальный entrypoint Grafana
exec /run.sh "$@"
