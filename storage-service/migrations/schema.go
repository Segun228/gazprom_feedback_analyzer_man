package migrations

import "github.com/ClickHouse/clickhouse-go/v2"

func Migrate(db clickhouse.Conn) {
	CreateProcessedDataTable(db)
}
