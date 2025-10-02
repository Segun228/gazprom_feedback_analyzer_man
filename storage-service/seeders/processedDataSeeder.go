package seeders

import (
	"context"
	"encoding/csv"
	"log/slog"
	"os"
	"strings"
	"time"

	"github.com/ClickHouse/clickhouse-go/v2"
	"github.com/Segun228/gazprom_feedback_analyzer_man/storage-service/config"
	"github.com/Segun228/gazprom_feedback_analyzer_man/storage-service/models"
	"github.com/Segun228/gazprom_feedback_analyzer_man/storage-service/store"
)

func SeedFromFile(db clickhouse.Conn, store *store.DataStore) {
	var count uint64
	ctx := context.Background()

	query := "SELECT count() FROM processed_data"

	if err := db.QueryRow(ctx, query).Scan(&count); err != nil {
		slog.Error("failed to check processed_data table", "error", err)
		os.Exit(1)
	}

	if config.Cfg.DB.Seeders.File == "" {
		slog.Info("seed file path is empty, skipping seeding")
		return
	}

	if count == 0 {
		slog.Info("seeding data from .csv file to database")
		f, err := os.Open(config.Cfg.DB.Seeders.File)
		if err != nil {
			slog.Warn("failed to open seed file, skipping seeding", "error", err)
			return
		}
		defer f.Close()

		reader := csv.NewReader(f)
		reader.Comma = ';'
		records, err := reader.ReadAll()
		if err != nil {
			slog.Warn("failed to read seed file, skipping seeding", "error", err)
			return
		}

		var data []models.Datum
		var count = 0

		for _, rec := range records {
			const layout = "2006-01-02 15:04:05"
			dateFiled, err := time.Parse(layout, rec[1])
			if err != nil {
				slog.Error("failed to parse date", "date", rec[1])
				continue
			}

			if len(rec) < 4 {
				slog.Error("invalid csv row, not enough columns", "row", rec)
				continue
			}

			var sentiments = map[string]uint8{
				"0": 0,
				"1": 1,
				"2": 2,
			}

			val, ok := sentiments[rec[2]]
			if !ok {
				slog.Error("invalid sentiment field format", "sentiment field", rec[2])
				continue
			}

			datum := models.Datum{
				Text:      rec[0],
				DateField: dateFiled,
				Sentiment: val,
				Tags:      strings.Split(rec[3], ","),
			}

			data = append(data, datum)
			count++
		}

		if err := store.AddMany(ctx, data); err != nil {
			slog.Error("failed to insert data", "first 10 records", data[:min(len(data), 10)])
			return
		}

		slog.Info("data seeded", "amount", count)
	}
}
