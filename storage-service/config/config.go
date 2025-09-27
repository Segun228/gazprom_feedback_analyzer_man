package config

import (
	"log/slog"
	"os"
	"strings"

	"github.com/spf13/viper"
)

type Config struct {
	HTTP struct {
		Port string `mapstructure:"port"`
	} `mapstructure:"http"`
	DB struct {
		Name     string `mapstructure:"name"`
		User     string `mapstructure:"user"`
		Password string `mapstructure:"password"`
		Port     string `mapstructure:"port"`
	} `mapstructure:"db"`
	Kafka struct {
		Brokers  string `mapstructure:"brokers"`
		GroupIDs struct {
			ModelsService string `mapstructure:"models_service"`
		} `mapstructure:"group_ids"`
		Topics struct {
			ProcessedData string `mapstructure:"processed_data"`
		} `mapstructure:"topics"`
	} `mapstructure:"kafka"`
}

var Cfg Config

func InitConfig() {
	viper.SetConfigName("config")
	viper.SetConfigType("yml")
	viper.AddConfigPath("./storage-service")

	viper.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))

	viper.AutomaticEnv()

	if err := viper.ReadInConfig(); err != nil {
		slog.Warn("config file not found. Relying on environment variables")
	}

	if err := viper.Unmarshal(&Cfg); err != nil {
		slog.Error("unable to decode config into struct", "error", err)
		os.Exit(1)
	}
}
