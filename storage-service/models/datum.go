package models

import "time"

type Datum struct {
	ID        uint64    `json:"id"`
	Text      string    `json:"text"`
	DateField time.Time `json:"date"`
	Sentiment uint8     `json:"sentiment"`
	Tags      []string  `json:"tags"`
}
