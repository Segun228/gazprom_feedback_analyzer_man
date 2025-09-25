package migrations

import (
	"context"
	"log/slog"
	"os"

	"github.com/ClickHouse/clickhouse-go/v2"
)

func CreateProcessedDataTable(db clickhouse.Conn) {
	ctx := context.Background()

	var exists uint8
	err := db.QueryRow(ctx, "EXISTS TABLE processed_data").Scan(&exists)
	if err != nil {
		slog.Error("failed to check if processed_data table exists", "error", err)
		os.Exit(1)
	}

	if exists != 1 {
		err = db.Exec(ctx, `
			CREATE TABLE processed_data (
				id UInt64 DEFAULT rand(),
				text String,
				date DateTime,
				sentiment UInt8,
				tags Array(String)
			) ENGINE = MergeTree()
			ORDER BY id
		`)
		if err != nil {
			slog.Error("failed to create processed_data table", "error", err)
			os.Exit(1)
		}

		slog.Info("processed_data table created successfully!")
	}
}
