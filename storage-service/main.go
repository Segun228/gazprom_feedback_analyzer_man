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

	"github.com/Segun228/gazprom_feedback_analyzer_man/storage-service/config"
	"github.com/Segun228/gazprom_feedback_analyzer_man/storage-service/database"
	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
)

func main() {
	config.InitLogger()
	config.InitConfig()

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	database.NewConnection()

	r := chi.NewRouter()

	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)

	r.Get("/health", func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprintf(w, "Storage service is up and running!")
	})

	httpServer := &http.Server{
		Addr:    ":" + config.Cfg.HTTP.Port,
		Handler: r,
	}

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
