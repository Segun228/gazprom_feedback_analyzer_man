package migrations

import (
	"log/slog"

	"github.com/ClickHouse/clickhouse-go/v2"
)

func Migrate(db clickhouse.Conn) {
	CreateProcessedDataTable(db)
}

func DropTables(db clickhouse.Conn) {
	DropProcessedDataTable(db)

	slog.Info("tables successfully dropped")
}
