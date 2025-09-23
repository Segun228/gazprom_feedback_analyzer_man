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
	err := db.QueryRow(ctx, "EXISTS TABLE proccessed_data").Scan(&exists)
	if err != nil {
		slog.Error("failed to check if proccessed_data table exists", "error", err)
		os.Exit(1)
	}

	if exists != 1 {
		err = db.Exec(ctx, `
			CREATE TABLE proccessed_data (
				id UInt64,
				text String,
				date DateTime,
				sentiment Int8,
				tags Array(String)
			) ENGINE = MergeTree()
			ORDER BY id
		`)
		if err != nil {
			slog.Error("failed to create proccessed_data table", "error", err)
			os.Exit(1)
		}

		slog.Info("proccessed_data table created successfully!")
	}
}
