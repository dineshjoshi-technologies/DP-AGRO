# LLM Router Dockerfile
# Build: docker build -t djtech/llm-router:latest -f spike-prototype/llm-router/Dockerfile .

FROM golang:1.22-alpine AS builder

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache gcc musl-dev

# Copy go mod files
COPY spike-prototype/llm-router/go.mod spike-prototype/llm-router/go.sum ./

# Download dependencies
RUN go mod download

# Copy source
COPY spike-prototype/llm-router/main.go .
COPY spike-prototype/llm-router/router/ ./router/
COPY spike-prototype/llm-router/selector/ ./selector/
COPY spike-prototype/llm-router/adapters/ ./adapters/
COPY spike-prototype/llm-router/config/ ./config/

# Build
RUN CGO_ENABLED=1 GOOS=linux go build -o llm-router .

# Runtime stage
FROM alpine:3.20

RUN apk add --no-cache ca-certificates

WORKDIR /app

COPY --from=builder /app/llm-router .
COPY spike-prototype/llm-router/config/router-config.json /etc/llm-router/config.json

# Create non-root user
RUN adduser -D -u 1000 router
USER router

EXPOSE 8081

ENV CONFIG_PATH=/etc/llm-router/config.json

ENTRYPOINT ["./llm-router"]