package api

import (
	"fmt"
	"net/http"

	"github.com/Segun228/gazprom_feedback_analyzer_man/storage-service/handlers"
	"github.com/Segun228/gazprom_feedback_analyzer_man/storage-service/store"
	"github.com/go-chi/chi/middleware"
	"github.com/go-chi/chi/v5"
)

func SetupRoutes(dataStore *store.DataStore) *chi.Mux {
	r := chi.NewRouter()

	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)

	r.Get("/health", func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprintf(w, "Storage service is up and running!")
	})

	dataHandler := handlers.NewDataHandler(dataStore)

	r.Get("/", dataHandler.GetAllData)
	r.Get("/{id}", dataHandler.GetDatumByID)
	r.Post("/", dataHandler.AddCSVData)
	r.Delete("/{id}", dataHandler.DeleteDatumByID)

	return r
}
