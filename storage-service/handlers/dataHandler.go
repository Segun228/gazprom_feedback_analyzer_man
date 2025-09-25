package handlers

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/Segun228/gazprom_feedback_analyzer_man/storage-service/models"
	"github.com/Segun228/gazprom_feedback_analyzer_man/storage-service/store"
	"github.com/go-chi/chi/v5"
)

type DataHandler struct {
	store *store.DataStore
}

func NewDataHandler(s *store.DataStore) *DataHandler {
	return &DataHandler{
		store: s,
	}
}

func (h *DataHandler) GetAllData(w http.ResponseWriter, r *http.Request) {
	data, err := h.store.GetAll(r.Context())
	if err != nil {
		slog.Error("failed to get all data", "error", err)
		http.Error(w, "Error getting all data", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(data)
}

func (h *DataHandler) GetDatumByID(w http.ResponseWriter, r *http.Request) {
	idRaw := chi.URLParam(r, "id")
	id, err := strconv.Atoi(idRaw)
	if err != nil {
		slog.Error("failed to convert raw id to integer", "error", err)
		http.Error(w, "Invalid id", http.StatusBadRequest)
		return
	}

	datum, err := h.store.GetByID(r.Context(), uint64(id))
	if err != nil {
		slog.Error("failed to get datum by id", "error", err)
		http.Error(w, "Error getting datum", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(datum)
}

func (h *DataHandler) AddCSVData(w http.ResponseWriter, r *http.Request) {
	file, fileHeader, err := r.FormFile("file")
	if err != nil {
		slog.Error("failed to format file", "error", err)
		http.Error(w, "Error formating file", http.StatusInternalServerError)
		return
	}
	defer file.Close()

	if !strings.HasSuffix(strings.ToLower(fileHeader.Filename), ".csv") {
		http.Error(w, "only .csv files are allowed", http.StatusBadRequest)
		return
	}

	reader := csv.NewReader(file)
	reader.Comma = ';'
	records, err := reader.ReadAll()
	if err != nil {
		slog.Error("failed to parse csv-file")
		http.Error(w, "Error parsing CSV-file", http.StatusBadRequest)
		return
	}

	var data []models.Datum
	var count = 0

	for _, rec := range records {
		const layout = "2006-01-02 15:04:05"
		dateFiled, err := time.Parse(layout, rec[1])
		if err != nil {
			slog.Error("failed to parse date", "date", rec[1])
			continue
		}

		if len(rec) < 4 {
			slog.Error("invalid csv row, not enough columns", "row", rec)
			continue
		}

		var sentiments = map[string]uint8{
			"0": 0,
			"1": 1,
			"2": 2,
		}

		val, ok := sentiments[rec[2]]
		if !ok {
			slog.Error("invalid sentiment field format", "sentiment field", rec[2])
			continue
		}

		datum := models.Datum{
			Text:      rec[0],
			DateField: dateFiled,
			Sentiment: val,
			Tags:      strings.Split(rec[3], ","),
		}

		data = append(data, datum)
		count++
	}

	if err := h.store.AddMany(r.Context(), data); err != nil {
		slog.Error("failed to insert data", "first 10 records", data[:min(len(data), 10)])
		http.Error(w, "Error inserting data", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(fmt.Sprintf("Data inserted: %d", count))
}

func (h *DataHandler) DeleteDatumByID(w http.ResponseWriter, r *http.Request) {
	idRaw := chi.URLParam(r, "id")
	id, err := strconv.Atoi(idRaw)
	if err != nil {
		slog.Error("failed to convert raw id to integer", "error", err)
		http.Error(w, "Invalid id", http.StatusBadRequest)
		return
	}

	err = h.store.DeleteByID(r.Context(), uint64(id))
	if err != nil {
		slog.Error("failed to delete datum by id", "error", err)
		http.Error(w, "Error deleting datum", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode("Data deletion successfully requested")
}
