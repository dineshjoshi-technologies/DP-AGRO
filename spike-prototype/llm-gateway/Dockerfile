# LLM Gateway Dockerfile
# Build: docker build -t djtech/llm-gateway:latest -f spike-prototype/llm-gateway/Dockerfile .

FROM golang:1.22-alpine AS builder

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache gcc musl-dev

# Copy go mod files
COPY spike-prototype/llm-gateway/go.mod spike-prototype/llm-gateway/go.sum ./

# Download dependencies
RUN go mod download

# Copy source
COPY spike-prototype/llm-gateway/main.go .

# Build
RUN CGO_ENABLED=1 GOOS=linux go build -o llm-gateway .

# Runtime stage
FROM alpine:3.20

RUN apk add --no-cache ca-certificates

WORKDIR /app

COPY --from=builder /app/llm-gateway .
COPY spike-prototype/llm-gateway/config.json /etc/llm-gateway/config.json

# Create non-root user
RUN adduser -D -u 1000 gateway
USER gateway

EXPOSE 8080

ENV CONFIG_PATH=/etc/llm-gateway/config.json

ENTRYPOINT ["./llm-gateway"]