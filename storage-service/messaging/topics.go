package messaging

import (
	"log/slog"
	"net"
	"os"
	"strconv"
	"strings"

	"github.com/Segun228/gazprom_feedback_analyzer_man/storage-service/config"
	"github.com/segmentio/kafka-go"
)

var (
	ProcessedDataTopic string
)

var Topics []string

func InitTopicsNames() {
	ProcessedDataTopic = config.Cfg.Kafka.Topics.ProcessedData

	Topics = []string{
		ProcessedDataTopic,
	}
}

func InitTopics() {
	if config.Cfg.Kafka.Brokers == "" {
		slog.Error("KAFKA_BROKERS environment variable is not set")
		os.Exit(1)
	}
	brokers := strings.Split(config.Cfg.Kafka.Brokers, ",")
	conn, err := kafka.Dial("tcp", brokers[0])
	if err != nil {
		slog.Error("failed to dial Kafka broker", "error", err)
		os.Exit(1)
	}
	defer conn.Close()

	controller, err := conn.Controller()
	if err != nil {
		slog.Error("failed to get Kafka controller", "error", err)
		os.Exit(1)
	}

	controllerConn, err := kafka.Dial("tcp", net.JoinHostPort(controller.Host, strconv.Itoa(controller.Port)))
	if err != nil {
		slog.Error("failed to dial Kafka controller", "error", err)
		os.Exit(1)
	}
	defer controllerConn.Close()

	topicConfigs := []kafka.TopicConfig{}
	for _, topic := range Topics {
		topicConfigs = append(topicConfigs, kafka.TopicConfig{
			Topic:             topic,
			NumPartitions:     1,
			ReplicationFactor: 1,
		})
	}

	err = controllerConn.CreateTopics(topicConfigs...)
	if err != nil {
		slog.Warn("topic cannot be created", "error", err)
	} else {
		slog.Info("topics successfully created or already exist")
	}
}
