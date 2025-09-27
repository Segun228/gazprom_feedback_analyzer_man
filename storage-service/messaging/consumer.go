package messaging

import (
	"context"
	"encoding/json"
	"log/slog"
	"os"
	"strings"
	"time"

	"github.com/Segun228/gazprom_feedback_analyzer_man/storage-service/config"
	"github.com/Segun228/gazprom_feedback_analyzer_man/storage-service/models"
	"github.com/Segun228/gazprom_feedback_analyzer_man/storage-service/store"
	"github.com/segmentio/kafka-go"
)

type ProcessedDataEvent struct {
	Batch []models.Datum `json:"batch"`
}

func StartConsumers(ctx context.Context, dataStore *store.DataStore) {
	go startTopicConsumer(ctx, ProcessedDataTopic, config.Cfg.Kafka.GroupIDs.ModelsService, func(ctx context.Context, msg kafka.Message) {
		handleProcessedData(ctx, msg, dataStore)
	})
}

func startTopicConsumer(ctx context.Context, topic, groupID string, handler func(ctx context.Context, msg kafka.Message)) {
	if config.Cfg.Kafka.Brokers == "" {
		slog.Error("KAFKA_BROKERS environment variable is not set")
		os.Exit(1)
	}

	brokers := strings.Split(config.Cfg.Kafka.Brokers, ",")

	r := kafka.NewReader(kafka.ReaderConfig{
		Brokers:        brokers,
		GroupID:        groupID,
		Topic:          topic,
		MinBytes:       10e3,
		MaxBytes:       10e6,
		CommitInterval: 1 * time.Second,
		StartOffset:    kafka.LastOffset,
	})

	slog.Info("Starting Kafka consumer", "topic", topic, "group_id", groupID)

	defer r.Close()

	for {
		select {
		case <-ctx.Done():
			slog.Info("stopping consumer due to context cancellation", "topic", topic)
			return
		default:
			m, err := r.ReadMessage(ctx)
			if err != nil {
				if ctx.Err() != nil {
					slog.Info("context cancelled, stopping consumer", "topic", topic)
					return
				}
				slog.Error("failed to read message", "topic", topic, "error", err)
				continue
			}
			slog.Info("processing message", "topic", topic)
			handler(ctx, m)

			if err := r.CommitMessages(ctx, m); err != nil {
				slog.Error("failed to commit message offset", "error", err)
			}
		}
	}
}

func handleProcessedData(ctx context.Context, msg kafka.Message, dataStore *store.DataStore) {
	slog.Info("handling data batch", "topic", ProcessedDataTopic)

	var event ProcessedDataEvent
	if err := json.Unmarshal(msg.Value, &event); err != nil {
		slog.Error("failed to unmarshal Kafka message", "error", err)
		return
	}
	slog.Info("processing batch of data", "count", len(event.Batch))

	if err := dataStore.AddMany(ctx, event.Batch); err != nil {
		slog.Error("failed to insert batch into Clickhouse", "error", err)
		return
	}

	slog.Info("data successfully inserted into database", "count", len(event.Batch))
}
