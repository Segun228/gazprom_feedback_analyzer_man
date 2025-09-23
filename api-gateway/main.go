package main

import (
	"context"
	"log/slog"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/Segun228/gazprom_feedback_analyzer_man/api-gateway/config"
	"github.com/go-chi/chi/v5"
)

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	config.InitLogger()
	config.InitConfig()

	if config.Cfg.URLs.StorageService == "" {
		slog.Error("STORAGE_SERVICE_URL is not set")
		os.Exit(1)
	}

	storageProxy := createReverseProxy(config.Cfg.URLs.StorageService)

	storageProxyHandler := http.StripPrefix("/storage", storageProxy)

	r := chi.NewRouter()

	r.Group(func(r chi.Router) {
		slog.Info("setting up public routes")

		r.Get("/storage/health", storageProxyHandler.ServeHTTP)
	})

	httpServer := &http.Server{
		Addr:    ":" + config.Cfg.HTTP.Port,
		Handler: r,
	}

	go func() {
		slog.Info("starting API Gateway", "port", config.Cfg.HTTP.Port)
		if err := httpServer.ListenAndServe(); err != nil {
			slog.Error("failed to start server", "error", err)
			os.Exit(1)
		}
	}()

	<-ctx.Done()

	slog.Info("shutting down servers...")

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := httpServer.Shutdown(shutdownCtx); err != nil {
		slog.Error("error shutting down servers", "error", err)
	}
	slog.Info("HTTP server stopped.")

	slog.Info("service gracefully stopped.")
}

func createReverseProxy(targetURL string) *httputil.ReverseProxy {
	remote, err := url.Parse(targetURL)
	if err != nil {
		slog.Error("failed to parse target url", "url", targetURL, "error", err)
		os.Exit(1)
	}

	return httputil.NewSingleHostReverseProxy(remote)
}
