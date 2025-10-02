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

	if config.Cfg.HTTP.PublicDomain == "" {
		slog.Error("HTTP_PUBLIC_DOMAIN is not set")
		os.Exit(1)
	}

	storageProxy := createReverseProxy(config.Cfg.URLs.StorageService)
	modelsProxy := createReverseProxy(config.Cfg.URLs.ModelsService)
	dashboardProxyHandler := createDashboardProxyHandler(config.Cfg.URLs.Dashboard)

	storageProxyHandler := http.StripPrefix("/storage", storageProxy)
	modelsProxyHandler := http.StripPrefix("/models", modelsProxy)

	r := chi.NewRouter()

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

		r.Handle("/dashboard", http.RedirectHandler("/dashboard/", http.StatusMovedPermanently))
		r.Handle("/dashboard/*", dashboardProxyHandler)
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

func createDashboardProxyHandler(targetURL string) http.Handler {
	slog.Info("Creating dashboard proxy handler", "target", targetURL)
	remote, err := url.Parse(targetURL)
	if err != nil {
		slog.Error("failed to parse target url", "url", targetURL, "error", err)
		os.Exit(1)
	}

	proxy := httputil.NewSingleHostReverseProxy(remote)

	internalHost := remote.Host
	publicDomain := config.Cfg.HTTP.PublicDomain

	proxy.ModifyResponse = func(resp *http.Response) error {
		location := resp.Header.Get("Location")
		if location != "" && len(location) > 0 {
			if strings.Contains(location, internalHost) {
				newLocation := strings.Replace(location, internalHost, publicDomain, 1)
				resp.Header.Set("Location", newLocation)
				slog.Info("Modified location header", "original", location, "modified", newLocation)
			}
		}
		return nil
	}

	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		slog.Info("Dashboard proxy request", "method", r.Method, "path", r.URL.Path)
		proxy.ServeHTTP(w, r)
	})
}
