package main

import (
	"context"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/Segun228/gazprom_feedback_analyzer_man/storage-service/api"
	"github.com/Segun228/gazprom_feedback_analyzer_man/storage-service/config"
	"github.com/Segun228/gazprom_feedback_analyzer_man/storage-service/database"
	"github.com/Segun228/gazprom_feedback_analyzer_man/storage-service/messaging"
	"github.com/Segun228/gazprom_feedback_analyzer_man/storage-service/migrations"
	"github.com/Segun228/gazprom_feedback_analyzer_man/storage-service/seeders"
	"github.com/Segun228/gazprom_feedback_analyzer_man/storage-service/store"
)

func main() {
	config.InitLogger()
	config.InitConfig()

	messaging.InitTopicsNames()

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	database.NewConnection()
	db := database.DB

	if config.Cfg.DB.DropEveryRelaunch {
		migrations.DropTables(db)
	}

	migrations.Migrate(db)

	slog.Info(fmt.Sprintf("%v", config.Cfg.DB.DropEveryRelaunch))

	dataStore := store.NewDataStore(db)
	seeders.Seed(db, dataStore)

	messaging.InitTopics()

	router := api.SetupRoutes(dataStore)

	httpServer := &http.Server{
		Addr:    ":" + config.Cfg.HTTP.Port,
		Handler: router,
	}

	messaging.StartConsumers(ctx, dataStore)

	go func() {
		slog.Info("starting storage service", "port", config.Cfg.HTTP.Port)

		if err := httpServer.ListenAndServe(); err != nil {
			slog.Error("failed to start service", "error", err)
			os.Exit(1)
		}
	}()

	<-ctx.Done()

	slog.Info("shutting down servers")

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := httpServer.Shutdown(shutdownCtx); err != nil {
		slog.Error("failed to shut down servers", "error", err)
	}
	slog.Info("HTTP server stopped")

	database.DB.Close()
	slog.Info("database connection closed")

	slog.Info("service grasefully stopped")
}
