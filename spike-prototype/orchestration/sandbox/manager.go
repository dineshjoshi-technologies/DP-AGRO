package sandbox

import (
	"context"
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/containerd/containerd/v2/client"
	"github.com/containerd/containerd/v2/pkg/oci"
	"github.com/google/uuid"
	"github.com/opencontainers/runtime-spec/specs-go"
)

// SandboxManager manages gVisor sandboxes via containerd
type SandboxManager struct {
	client      *client.Client
	config      *ManagerConfig
	sandboxes   map[string]*Sandbox
	mu          sync.RWMutex
	closed      bool
}

// ManagerConfig holds sandbox manager configuration
type ManagerConfig struct {
	ContainerdSocket string
	GVisorRuntime    string
	BaseImage        string
	NetworkProfile   string
	DefaultCPU       string
	DefaultMemory    string
	DefaultDisk      string
	DefaultTimeout   time.Duration
	MaxConcurrent    int
}

// Sandbox represents a running agent sandbox
type Sandbox struct {
	ID          string
	Container   containerd.Container
	Task        containerd.Task
	AgentID     string
	Config      SandboxConfig
	CreatedAt   time.Time
	StartedAt   *time.Time
	CompletedAt *time.Time
	Status      SandboxStatus
	Resources   ResourceUsage
	mu          sync.RWMutex
}

// SandboxConfig holds configuration for a single sandbox
type SandboxConfig struct {
	CPU       string
	Memory    string
	Disk      string
	Timeout   time.Duration
	Network   string
	Env       map[string]string
	Secrets   map[string]string
	Workdir   string
	Command   []string
	Args      []string
}

// SandboxStatus represents the status of a sandbox
type SandboxStatus string

const (
	SandboxStatusCreating   SandboxStatus = "creating"
	SandboxStatusRunning    SandboxStatus = "running"
	SandboxStatusCompleted  SandboxStatus = "completed"
	SandboxStatusFailed     SandboxStatus = "failed"
	SandboxStatusTerminated SandboxStatus = "terminated"
)

// ResourceUsage tracks resource consumption
type ResourceUsage struct {
	CPUSeconds      float64
	MemoryGBSeconds float64
	DiskBytes       int64
	NetworkBytesIn  int64
	NetworkBytesOut int64
	LLMTokensIn     int64
	LLMTokensOut    int64
}

// NewManager creates a new sandbox manager
func NewManager(config *ManagerConfig) (*SandboxManager, error) {
	// Set defaults
	if config.ContainerdSocket == "" {
		config.ContainerdSocket = "/run/containerd/containerd.sock"
	}
	if config.GVisorRuntime == "" {
		config.GVisorRuntime = "runsc"
	}
	if config.BaseImage == "" {
		config.BaseImage = "djtech/agent-base:latest"
	}
	if config.MaxConcurrent == 0 {
		config.MaxConcurrent = 50
	}
	if config.DefaultTimeout == 0 {
		config.DefaultTimeout = 24 * time.Hour
	}

	// Connect to containerd
	cli, err := client.New(config.ContainerdSocket, client.WithDefaultNamespace("agents"))
	if err != nil {
		return nil, fmt.Errorf("failed to connect to containerd: %w", err)
	}

	m := &SandboxManager{
		client:    cli,
		config:    config,
		sandboxes: make(map[string]*Sandbox),
	}

	// Start cleanup routine
	go m.cleanupRoutine()

	return m, nil
}

// CreateSandbox creates a new sandbox for an agent
func (m *SandboxManager) CreateSandbox(ctx context.Context, agentID string, config SandboxConfig) (*Sandbox, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if m.closed {
		return nil, fmt.Errorf("sandbox manager is closed")
	}

	if len(m.sandboxes) >= m.config.MaxConcurrent {
		return nil, fmt.Errorf("max concurrent sandboxes reached (%d)", m.config.MaxConcurrent)
	}

	// Apply defaults
	if config.CPU == "" {
		config.CPU = m.config.DefaultCPU
	}
	if config.Memory == "" {
		config.Memory = m.config.DefaultMemory
	}
	if config.Disk == "" {
		config.Disk = m.config.DefaultDisk
	}
	if config.Timeout == 0 {
		config.Timeout = m.config.DefaultTimeout
	}
	if config.Network == "" {
		config.Network = m.config.NetworkProfile
	}

	// Generate sandbox ID
	sandboxID := "sandbox-" + uuid.New().String()[:12]

	// Create container spec
	spec, err := m.createSpec(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create OCI spec: %w", err)
	}

	// Create container
	container, err := m.client.NewContainer(
		ctx,
		sandboxID,
		client.WithImage(config.BaseImage, m.config.BaseImage),
		client.WithRuntime(m.config.GVisorRuntime, nil),
		client.WithSpec(spec),
		client.WithNewSnapshot(sandboxID),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create container: %w", err)
	}

	// Create task
	task, err := container.NewTask(ctx, client.NewIO())
	if err != nil {
		container.Delete(ctx, client.WithSnapshotCleanup)
		return nil, fmt.Errorf("failed to create task: %w", err)
	}

	// Start task
	if err := task.Start(ctx); err != nil {
		task.Delete(ctx)
		container.Delete(ctx, client.WithSnapshotCleanup)
		return nil, fmt.Errorf("failed to start task: %w", err)
	}

	now := time.Now()
	sandbox := &Sandbox{
		ID:        sandboxID,
		Container: container,
		Task:      task,
		AgentID:   agentID,
		Config:    config,
		CreatedAt: now,
		StartedAt: &now,
		Status:    SandboxStatusRunning,
	}

	m.sandboxes[sandboxID] = sandbox

	log.Printf("Created sandbox %s for agent %s", sandboxID, agentID)
	return sandbox, nil
}

// createSpec creates an OCI spec for the sandbox
func (m *SandboxManager) createSpec(config SandboxConfig) (*specs.Spec, error) {
	// Base spec
	spec := oci.GenerateSpec(oci.WithDefaultCapabilities, oci.WithDefaultUnixDevices)

	// Set process
	spec.Process = &specs.Process{
		Args: config.Command,
		Env:  m.envToSlice(config.Env),
		Cwd:  config.Workdir,
	}

	// Set resource limits
	spec.Linux = &specs.Linux{
		Resources: &specs.LinuxResources{
			CPU: &specs.LinuxCPU{
				Quota: m.parseCPUQuota(config.CPU),
			},
			Memory: &specs.LinuxMemory{
				Limit: m.parseMemoryLimit(config.Memory),
			},
			Pids: &specs.LinuxPids{
				Limit: 256,
			},
		},
	}

	// Set network namespace (default-deny handled by eBPF/Cilium)
	if config.Network != "host" {
		spec.Linux.Namespaces = append(spec.Linux.Namespaces, specs.LinuxNamespace{
			Type: specs.NetworkNamespace,
		})
	}

	// Mount workspace and secrets
	spec.Mounts = append(spec.Mounts,
		specs.Mount{
			Destination: config.Workdir,
			Type:        "bind",
			Source:      config.Workdir,
			Options:     []string{"rbind", "ro"},
		},
		specs.Mount{
			Destination: "/secrets",
			Type:        "tmpfs",
			Source:      "tmpfs",
			Options:     []string{"nosuid", "noexec", "nodev", "mode=0700"},
		},
	)

	return spec, nil
}

// envToSlice converts env map to slice
func (m *SandboxManager) envToSlice(env map[string]string) []string {
	result := make([]string, 0, len(env))
	for k, v := range env {
		result = append(result, fmt.Sprintf("%s=%s", k, v))
	}
	return result
}

// parseCPUQuota parses CPU string like "1000m" to quota
func (m *SandboxManager) parseCPUQuota(cpu string) *int64 {
	// Parse Kubernetes-style CPU (e.g., "1000m" = 1 core, "500m" = 0.5 core)
	var quota int64
	if len(cpu) > 1 && cpu[len(cpu)-1] == 'm' {
		// Millicores
		fmt.Sscanf(cpu[:len(cpu)-1], "%d", &quota)
		quota = quota * 1000 // Convert to microseconds
	} else {
		// Cores
		var cores float64
		fmt.Sscanf(cpu, "%f", &cores)
		quota = int64(cores * 100000) // 100000 = 1 core in microseconds
	}
	return &quota
}

// parseMemoryLimit parses memory string like "512Mi" to bytes
func (m *SandboxManager) parseMemoryLimit(memory string) *int64 {
	var limit int64
	var unit string
	fmt.Sscanf(memory, "%d%s", &limit, &unit)

	switch unit {
	case "Ki", "K":
		limit *= 1024
	case "Mi", "M":
		limit *= 1024 * 1024
	case "Gi", "G":
		limit *= 1024 * 1024 * 1024
	case "Ti", "T":
		limit *= 1024 * 1024 * 1024 * 1024
	}
	return &limit
}

// GetSandbox returns a sandbox by ID
func (m *SandboxManager) GetSandbox(id string) (*Sandbox, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	s, ok := m.sandboxes[id]
	return s, ok
}

// ListSandboxes returns all sandboxes
func (m *SandboxManager) ListSandboxes() []*Sandbox {
	m.mu.RLock()
	defer m.mu.RUnlock()
	result := make([]*Sandbox, 0, len(m.sandboxes))
	for _, s := range m.sandboxes {
		result = append(result, s)
	}
	return result
}

// TerminateSandbox terminates a sandbox
func (m *SandboxManager) TerminateSandbox(ctx context.Context, id string) error {
	m.mu.Lock()
	sandbox, ok := m.sandboxes[id]
	if !ok {
		m.mu.Unlock()
		return fmt.Errorf("sandbox not found: %s", id)
	}
	delete(m.sandboxes, id)
	m.mu.Unlock()

	sandbox.mu.Lock()
	defer sandbox.mu.Unlock()

	now := time.Now()
	sandbox.CompletedAt = &now
	sandbox.Status = SandboxStatusTerminated

	// Kill task
	if sandbox.Task != nil {
		if err := sandbox.Task.Kill(ctx, 9); err != nil {
			log.Printf("Warning: failed to kill task %s: %v", sandbox.ID, err)
		}
		sandbox.Task.Delete(ctx)
	}

	// Delete container
	if sandbox.Container != nil {
		if err := sandbox.Container.Delete(ctx, client.WithSnapshotCleanup); err != nil {
			log.Printf("Warning: failed to delete container %s: %v", sandbox.ID, err)
		}
	}

	log.Printf("Terminated sandbox %s", id)
	return nil
}

// WaitSandbox waits for a sandbox to complete
func (m *SandboxManager) WaitSandbox(ctx context.Context, id string) (*Sandbox, error) {
	sandbox, ok := m.GetSandbox(id)
	if !ok {
		return nil, fmt.Errorf("sandbox not found: %s", id)
	}

	// Wait for task to exit
	statusC, err := sandbox.Task.Wait(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to wait for task: %w", err)
	}

	select {
	case status := <-statusC:
		sandbox.mu.Lock()
		defer sandbox.mu.Unlock()
		now := time.Now()
		sandbox.CompletedAt = &now
		if status.ExitCode() == 0 {
			sandbox.Status = SandboxStatusCompleted
		} else {
			sandbox.Status = SandboxStatusFailed
		}
		return sandbox, nil
	case <-ctx.Done():
		return sandbox, ctx.Err()
	}
}

// CollectResources collects resource usage for a sandbox
func (m *SandboxManager) CollectResources(ctx context.Context, id string) (*ResourceUsage, error) {
	sandbox, ok := m.GetSandbox(id)
	if !ok {
		return nil, fmt.Errorf("sandbox not found: %s", id)
	}

	// Get metrics from containerd
	metrics, err := sandbox.Task.Metrics(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to get metrics: %w", err)
	}

	// Calculate usage
	usage := &ResourceUsage{}
	for _, m := range metrics {
		if m.Name == "cpu.usage.total" {
			usage.CPUSeconds = float64(m.Value) / 1e9 // nanoseconds to seconds
		}
		if m.Name == "memory.usage" {
			usage.MemoryGBSeconds = float64(m.Value) / (1024 * 1024 * 1024)
		}
	}

	sandbox.mu.Lock()
	sandbox.Resources = *usage
	sandbox.mu.Unlock()

	return usage, nil
}

// Close closes the sandbox manager
func (m *SandboxManager) Close() error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if m.closed {
		return nil
	}
	m.closed = true

	// Terminate all sandboxes
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	for id := range m.sandboxes {
		m.TerminateSandbox(ctx, id)
	}

	if m.client != nil {
		m.client.Close()
	}

	return nil
}

// cleanupRoutine periodically cleans up completed sandboxes
func (m *SandboxManager) cleanupRoutine() {
	ticker := time.NewTicker(1 * time.Minute)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			m.cleanup()
		}
	}
}

// cleanup removes completed/failed sandboxes older than 5 minutes
func (m *SandboxManager) cleanup() {
	m.mu.Lock()
	defer m.mu.Unlock()

	now := time.Now()
	for id, sandbox := range m.sandboxes {
		sandbox.mu.RLock()
		completed := sandbox.CompletedAt
		status := sandbox.Status
		sandbox.mu.RUnlock()

		if completed != nil && (status == SandboxStatusCompleted || status == SandboxStatusFailed || status == SandboxStatusTerminated) {
			if now.Sub(*completed) > 5*time.Minute {
				delete(m.sandboxes, id)
				log.Printf("Cleaned up sandbox %s", id)
			}
		}
	}
}

// Stats returns sandbox manager statistics
func (m *SandboxManager) Stats() map[string]interface{} {
	m.mu.RLock()
	defer m.mu.RUnlock()

	stats := map[string]interface{}{
		"total_sandboxes":   len(m.sandboxes),
		"running":           0,
		"completed":         0,
		"failed":            0,
		"max_concurrent":    m.config.MaxConcurrent,
	}

	for _, s := range m.sandboxes {
		s.mu.RLock()
		switch s.Status {
		case SandboxStatusRunning:
			stats["running"] = stats["running"].(int) + 1
		case SandboxStatusCompleted:
			stats["completed"] = stats["completed"].(int) + 1
		case SandboxStatusFailed:
			stats["failed"] = stats["failed"].(int) + 1
		}
		s.mu.RUnlock()
	}

	return stats
}

// Sandbox methods

// Status returns the sandbox status
func (s *Sandbox) Status() SandboxStatus {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.Status
}

// Resources returns resource usage
func (s *Sandbox) Resources() ResourceUsage {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.Resources
}

// ID returns the sandbox ID
func (s *Sandbox) ID() string {
	return s.ID
}

// AgentID returns the agent ID
func (s *Sandbox) AgentID() string {
	return s.AgentID
}