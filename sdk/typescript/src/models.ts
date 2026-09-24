/**
 * TypeScript models for DJ Tech Agent Runtime API
 */

export enum SecurityTier {
  STANDARD = 'standard',
  HIGH = 'high',
  SYSTEM = 'system',
}

export enum AgentStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  STOPPED = 'stopped',
  FAILED = 'failed',
  DELETED = 'deleted',
}

export enum JobStatus {
  PENDING = 'pending',
  SCHEDULED = 'scheduled',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  DEAD_LETTER = 'dead_letter',
  CANCELLED = 'cancelled',
}

export enum ToolType {
  BUILTIN = 'builtin',
  SANDBOXED = 'sandboxed',
  MCP = 'mcp',
}

export enum LogLevel {
  DEBUG = 'debug',
  INFO = 'info',
  WARN = 'warn',
  ERROR = 'error',
}

export enum OperationStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
}

export enum HealthStatus {
  HEALTHY = 'healthy',
  DEGRADED = 'degraded',
  UNHEALTHY = 'unhealthy',
}

export enum HealthCheckStatus {
  PASS = 'pass',
  WARN = 'warn',
  FAIL = 'fail',
}

export interface AgentRuntime {
  image: string;
  entrypoint: string[];
  env?: Record<string, string>;
}

export interface ResourceLimits {
  cpu?: string;
  memory?: string;
  disk?: string;
  max_execution_time?: string;
}

export interface LLMConfig {
  default_model?: string;
  max_tokens_per_request?: number;
  monthly_budget_usd?: number;
  allowed_models?: string[];
}

export interface ToolConfig {
  name: string;
  type?: ToolType;
  config?: Record<string, unknown>;
}

export interface NetworkConfig {
  egress_allowlist?: string[];
}

export interface AutoscalingConfig {
  min_replicas?: number;
  max_replicas?: number;
  scale_up_delay_seconds?: number;
}

export interface CreateAgentRequest {
  name: string;
  description?: string;
  security_tier?: SecurityTier;
  runtime: AgentRuntime;
  resources?: ResourceLimits;
  llm?: LLMConfig;
  tools?: ToolConfig[];
  networking?: NetworkConfig;
  autoscaling?: AutoscalingConfig;
}

export interface UpdateAgentRequest {
  description?: string;
  resources?: ResourceLimits;
  llm?: LLMConfig;
  tools?: ToolConfig[];
  networking?: NetworkConfig;
  autoscaling?: AutoscalingConfig;
}

export interface StopAgentRequest {
  force?: boolean;
  timeout_seconds?: number;
}

export interface Agent {
  id: string;
  name: string;
  description?: string;
  status: AgentStatus;
  security_tier: SecurityTier;
  runtime: AgentRuntime;
  resources: ResourceLimits;
  llm: LLMConfig;
  tools: ToolConfig[];
  networking: NetworkConfig;
  autoscaling: AutoscalingConfig;
  created_at: string;
  updated_at: string;
  started_at?: string;
  stopped_at?: string;
}

export interface Pagination {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface AgentListResponse {
  agents: Agent[];
  pagination: Pagination;
}

export interface Operation {
  id: string;
  type: string;
  status: OperationStatus;
  created_at: string;
  updated_at: string;
}

export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  source: string;
  metadata?: Record<string, unknown>;
}

export interface LogStreamResponse {
  logs: LogEntry[];
  next_cursor?: string;
}

export interface ExecRequest {
  command: string[];
  env?: Record<string, string>;
  timeout_seconds?: number;
}

export interface ExecResponse {
  exit_code: number;
  stdout: string;
  stderr: string;
  duration_ms: number;
}

export interface RetryPolicy {
  max_attempts?: number;
  base_delay_seconds?: number;
  max_delay_seconds?: number;
  multiplier?: number;
  jitter?: number;
  retryable_errors?: string[];
}

export interface Job {
  id: string;
  type: string;
  payload: Record<string, unknown>;
  priority?: number;
  status: JobStatus;
  created_at: string;
  updated_at: string;
  scheduled_at?: string;
  started_at?: string;
  completed_at?: string;
  attempts?: number;
  max_attempts?: number;
  timeout_seconds?: number;
  retry_policy?: RetryPolicy;
  idempotency_key?: string;
  result?: Record<string, unknown>;
  error?: string;
  metadata?: Record<string, unknown>;
}

export interface SubmitJobRequest {
  type: string;
  payload: Record<string, unknown>;
  priority?: number;
  scheduled_at?: string;
  timeout_seconds?: number;
  retry_policy?: RetryPolicy;
  idempotency_key?: string;
  metadata?: Record<string, unknown>;
}

export interface UsageBreakdown {
  agent_id: string;
  agent_name: string;
  event_type: string;
  quantity: number;
  unit_cost_usd: number;
  total_cost_usd: number;
}

export interface UsageResponse {
  period_start: string;
  period_end: string;
  total_cost_usd: number;
  breakdown: UsageBreakdown[];
}

export interface Template {
  id: string;
  name: string;
  description: string;
  category: string;
  runtime: AgentRuntime;
  default_config?: Record<string, unknown>;
}

export interface TemplateListResponse {
  templates: Template[];
}

export interface HealthCheck {
  name: string;
  status: HealthCheckStatus;
  message?: string;
}

export interface HealthResponse {
  status: HealthStatus;
  version: string;
  timestamp: string;
  checks: HealthCheck[];
}

export interface ErrorResponse {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}