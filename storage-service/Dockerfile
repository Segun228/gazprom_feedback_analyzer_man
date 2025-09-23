FROM golang:1.24-alpine AS builder

WORKDIR /app

COPY storage-service/go.mod storage-service/go.sum ./storage-service/

RUN echo "go 1.24.0" >> go.work
RUN echo "use (" >> go.work
RUN echo "  ./storage-service" >> go.work
RUN echo ")" >> go.work

RUN go mod download

COPY storage-service/ ./storage-service/
COPY storage-service/config.yaml ./storage-service/config.yaml

RUN CGO_ENABLED=0 GOOS=linux go build -o /app/main ./storage-service

FROM alpine:latest

WORKDIR /app

COPY --from=builder /app/main .
COPY --from=builder /app/storage-service/config.yaml ./storage-service/config.yaml

EXPOSE 3001

CMD ["/app/main"]