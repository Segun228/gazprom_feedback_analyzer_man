package seeders

import (
	"github.com/ClickHouse/clickhouse-go/v2"
	"github.com/Segun228/gazprom_feedback_analyzer_man/storage-service/store"
)

func Seed(db clickhouse.Conn, store *store.DataStore) {
	SeedFromFile(db, store)
}
