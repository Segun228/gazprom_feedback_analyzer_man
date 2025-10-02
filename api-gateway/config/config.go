package config

import (
	"log/slog"
	"os"
	"strings"

	"github.com/spf13/viper"
)

type Config struct {
	HTTP struct {
		Port         string `mapstructure:"port"`
		PublicDomain string `mapstructure:"public_domain"`
	} `mapstructure:"http"`
	URLs struct {
		StorageService string `mapstructure:"storage_service"`
		Dashboard      string `mapstructure:"dashboard"`
		ModelsService  string `mapstructure:"models_service"`
		HealthService  string `mapstructure:"health_service"`
	} `mapstructure:"urls"`
}

var Cfg Config

func InitConfig() {
	viper.SetConfigName("config")
	viper.SetConfigType("yml")
	viper.AddConfigPath("./api-gateway")

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
