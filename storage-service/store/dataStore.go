package store

import (
	"context"

	"github.com/ClickHouse/clickhouse-go/v2"
	"github.com/Segun228/gazprom_feedback_analyzer_man/storage-service/models"
)

type DataStore struct {
	db clickhouse.Conn
}

func NewDataStore(db clickhouse.Conn) *DataStore {
	return &DataStore{db: db}
}

func (s *DataStore) GetAll(ctx context.Context) ([]models.Datum, error) {
	query := `
		SELECT
		id, text, date, sentiment, tags
		FROM processed_data
	`

	rows, err := s.db.Query(ctx, query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var data []models.Datum
	for rows.Next() {
		var datum models.Datum
		if err := rows.Scan(
			&datum.ID,
			&datum.Text,
			&datum.DateField,
			&datum.Sentiment,
			&datum.Tags,
		); err != nil {
			return nil, err
		}
		data = append(data, datum)
	}

	return data, nil
}

func (s *DataStore) GetByID(ctx context.Context, id uint64) (models.Datum, error) {
	query := `
		SELECT
		text, date, sentiment, tags
		FROM processed_data
		WHERE id = ?
	`

	datum := models.Datum{
		ID: id,
	}

	err := s.db.QueryRow(ctx, query, id).Scan(
		&datum.Text,
		&datum.DateField,
		&datum.Sentiment,
		&datum.Tags,
	)

	return datum, err
}

func (s *DataStore) Add(ctx context.Context, datum *models.Datum) error {
	query := `
		INSERT INTO processed_data
		(id, text, date, sentiment, tags)
		VALUES
		(?, ?, ?, ?, ?)
	`

	err := s.db.Exec(ctx, query, datum.ID, datum.Text, datum.DateField, datum.Sentiment, datum.Tags)

	return err
}

func (s *DataStore) AddMany(ctx context.Context, data []models.Datum) error {
	query := `
		INSERT INTO processed_data
		(text, date, sentiment, tags)
		VALUES
		(?, ?, ?, ?)
	`

	batch, err := s.db.PrepareBatch(ctx, query)
	if err != nil {
		return err
	}

	for _, datum := range data {
		if err := batch.Append(
			datum.Text,
			datum.DateField,
			datum.Sentiment,
			datum.Tags,
		); err != nil {
			return err
		}
	}

	return batch.Send()
}

func (s *DataStore) DeleteByID(ctx context.Context, id uint64) error {
	query := `
		ALTER TABLE processed_data 
		DELETE WHERE id = ?
	`

	err := s.db.Exec(ctx, query, id)
	return err
}
