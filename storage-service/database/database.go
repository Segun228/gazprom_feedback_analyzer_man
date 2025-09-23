package database

import (
	"context"
	"log/slog"
	"os"
	"time"

	"github.com/ClickHouse/clickhouse-go/v2"
	"github.com/Segun228/gazprom_feedback_analyzer_man/storage-service/config"
	"github.com/Segun228/gazprom_feedback_analyzer_man/storage-service/migrations"
)

var DB clickhouse.Conn

func NewConnection() {
	conn, err := clickhouse.Open(&clickhouse.Options{
		Addr: []string{"clickhouse:" + config.Cfg.DB.Port},
		Auth: clickhouse.Auth{
			Database: config.Cfg.DB.Name,
			Username: config.Cfg.DB.User,
			Password: config.Cfg.DB.Password,
		},
		DialTimeout:     5 * time.Second,
		ConnMaxLifetime: time.Hour,
	})
	if err != nil {
		slog.Error("failed to connect to clickhouse db", "error", err)
		os.Exit(1)
	}

	ctx := context.Background()

	if err := conn.Ping(ctx); err != nil {
		slog.Error("failed to ping clickhouse database", "error", err)
		os.Exit(1)
	}

	DB = conn

	slog.Info("Successfully connected to ClickHouse!")

	migrations.Migrate(DB)
}
