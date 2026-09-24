module github.com/djtech/orchestration

go 1.22

require (
	github.com/containerd/containerd/v2 v2.4.1
	github.com/docker/docker v24.0.7+incompatible
	github.com/google/uuid v1.5.0
	github.com/djtech/llm-router v0.0.0
	github.com/djtech/llm-gateway v0.0.0
	github.com/djtech/job-queue v0.0.0
)

replace github.com/djtech/llm-router => ../llm-router
replace github.com/djtech/llm-gateway => ../llm-gateway
replace github.com/djtech/job-queue => ../job-queue

require (
	github.com/cespare/xxhash/v2 v2.2.0 // indirect
	github.com/containerd/continuity v0.4.1 // indirect
	github.com/containerd/plugin v0.6.0 // indirect
	github.com/containerd/plugin-registry v0.6.0 // indirect
	github.com/containerd/ttrpc v1.2.4 // indirect
	github.com/containerd/typeurl/v2 v2.2.3 // indirect
	github.com/dgryski/go-rendezvous v0.0.0-20200823014737-9f7001d12a5f // indirect
	github.com/moby/locker v0.0.0-20211001012152-76b59b681b15 // indirect
	github.com/moby/term v0.0.0-20221205130635-1aeaba878587 // indirect
	github.com/opencontainers/go-digest v1.0.0 // indirect
	github.com/opencontainers/image-spec v1.0.2 // indirect
	github.com/opencontainers/runtime-spec v1.0.2 // indirect
	github.com/pkg/errors v0.9.1 // indirect
	golang.org/x/sys v0.15.0 // indirect
	google.golang.org/protobuf v1.31.0 // indirect
)