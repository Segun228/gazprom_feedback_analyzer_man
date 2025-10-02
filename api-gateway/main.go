package main

import (
	"context"
	"log/slog"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"os/signal"
	"strings"
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

	if config.Cfg.URLs.Dashboard == "" {
		slog.Error("SUPERSET_DASHBOARD_URL is not set")
		os.Exit(1)
	}

	if config.Cfg.URLs.ModelsService == "" {
		slog.Error("MODELS_SERVICE_URL is not set")
		os.Exit(1)
	}

	storageProxy := createReverseProxy(config.Cfg.URLs.StorageService)
	modelsProxy := createReverseProxy(config.Cfg.URLs.ModelsService)

	storageProxyHandler := http.StripPrefix("/storage", storageProxy)
	modelsProxyHandler := http.StripPrefix("/models", modelsProxy)

	r := chi.NewRouter()

	r.Use(func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if after, ok := strings.CutPrefix(r.URL.Path, "/dashboard"); ok {
				path := after
				if path == "" {
					path = "/"
				}
				redirectURL := "http://localhost:8088" + path
				if r.URL.RawQuery != "" {
					redirectURL += "?" + r.URL.RawQuery
				}
				slog.Info("Redirecting superset request", "from", r.URL.Path, "to", redirectURL)
				http.Redirect(w, r, redirectURL, http.StatusMovedPermanently)
				return
			}
			next.ServeHTTP(w, r)
		})
	})

	r.Group(func(r chi.Router) {
		slog.Info("setting up public routes")

		r.Get("/storage/health", storageProxyHandler.ServeHTTP)

		r.Get("/storage", storageProxyHandler.ServeHTTP)
		r.Get("/storage/{id}", storageProxyHandler.ServeHTTP)
		r.Post("/storage", storageProxyHandler.ServeHTTP)
		r.Delete("/storage/{id}", storageProxyHandler.ServeHTTP)

		r.Get("/models/health", modelsProxyHandler.ServeHTTP)
		r.Post("/models/predict", modelsProxyHandler.ServeHTTP)
		r.Post("/models/predict_single", modelsProxyHandler.ServeHTTP)
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
