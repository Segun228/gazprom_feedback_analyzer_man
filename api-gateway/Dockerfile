FROM golang:1.24-alpine AS builder

WORKDIR /app

COPY api-gateway/go.mod api-gateway/go.sum ./api-gateway/

RUN echo "go 1.24" >> go.work
RUN echo "use (" >> go.work
RUN echo "  ./api-gateway" >> go.work
RUN echo ")" >> go.work

RUN go mod download

COPY api-gateway/ ./api-gateway/
COPY api-gateway/config.yaml ./api-gateway/config.yaml

RUN CGO_ENABLED=0 GOOS=linux go build -o /app/main ./api-gateway

FROM alpine:latest

WORKDIR /app

COPY --from=builder /app/main .
COPY --from=builder /app/api-gateway/config.yaml ./api-gateway/config.yaml

EXPOSE 3000

CMD ["/app/main"]