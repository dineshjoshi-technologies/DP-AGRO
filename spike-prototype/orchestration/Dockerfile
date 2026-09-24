# Orchestration Service Dockerfile
# Build: docker build -t djtech/orchestration:latest -f spike-prototype/orchestration/Dockerfile .

FROM golang:1.22-alpine AS builder

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache gcc musl-dev

# Copy go mod files
COPY spike-prototype/orchestration/go.mod spike-prototype/orchestration/go.sum ./

# Download dependencies
RUN go mod download

# Copy source
COPY spike-prototype/orchestration/main.go .
COPY spike-prototype/orchestration/config/ ./config/
COPY spike-prototype/orchestration/sandbox/ ./sandbox/
COPY spike-prototype/orchestration/executor/ ./executor/
COPY spike-prototype/orchestration/billing/ ./billing/

# Copy dependent modules
COPY spike-prototype/llm-router/ ../llm-router/
COPY spike-prototype/llm-gateway/ ../llm-gateway/
COPY spike-prototype/job-queue/ ../job-queue/

# Build
RUN CGO_ENABLED=1 GOOS=linux go build -o orchestration .

# Runtime stage
FROM alpine:3.20

RUN apk add --no-cache ca-certificates

WORKDIR /app

COPY --from=builder /app/orchestration .
COPY spike-prototype/orchestration/config/config.json /etc/orchestration/config.json

# Create non-root user
RUN adduser -D -u 1000 orchestration
USER orchestration

EXPOSE 8082

ENV CONFIG_PATH=/etc/orchestration/config.json

ENTRYPOINT ["./orchestration"]