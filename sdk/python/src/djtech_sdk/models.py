"""
Pydantic models for DJ Tech Agent Runtime API
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, HttpUrl
from uuid import UUID


class SecurityTier(str, Enum):
    STANDARD = "standard"
    HIGH = "high"
    SYSTEM = "system"


class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    DELETED = "deleted"


class JobStatus(str, Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"
    CANCELLED = "cancelled"


class ToolType(str, Enum):
    BUILTIN = "builtin"
    SANDBOXED = "sandboxed"
    MCP = "mcp"


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


class OperationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthCheckStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class AgentRuntime(BaseModel):
    image: str
    entrypoint: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)


class ResourceLimits(BaseModel):
    cpu: str = "1000m"
    memory: str = "2Gi"
    disk: str = "1Gi"
    max_execution_time: str = "24h"


class LLMConfig(BaseModel):
    default_model: str = "gpt-4o-mini"
    max_tokens_per_request: int = 8192
    monthly_budget_usd: float = 50.0
    allowed_models: List[str] = Field(default_factory=lambda: ["gpt-4o-mini", "gpt-4o", "claude-3.5-sonnet"])


class ToolConfig(BaseModel):
    name: str
    type: ToolType = ToolType.BUILTIN
    config: Dict[str, Any] = Field(default_factory=dict)


class NetworkConfig(BaseModel):
    egress_allowlist: List[str] = Field(default_factory=list)


class AutoscalingConfig(BaseModel):
    min_replicas: int = 0
    max_replicas: int = 10
    scale_up_delay_seconds: int = 30


class CreateAgentRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    security_tier: SecurityTier = SecurityTier.STANDARD
    runtime: AgentRuntime
    resources: Optional[ResourceLimits] = None
    llm: Optional[LLMConfig] = None
    tools: List[ToolConfig] = Field(default_factory=list)
    networking: Optional[NetworkConfig] = None
    autoscaling: Optional[AutoscalingConfig] = None


class UpdateAgentRequest(BaseModel):
    description: Optional[str] = Field(None, max_length=500)
    resources: Optional[ResourceLimits] = None
    llm: Optional[LLMConfig] = None
    tools: List[ToolConfig] = Field(default_factory=list)
    networking: Optional[NetworkConfig] = None
    autoscaling: Optional[AutoscalingConfig] = None


class StopAgentRequest(BaseModel):
    force: bool = False
    timeout_seconds: int = Field(30, ge=1, le=300)


class Agent(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    status: AgentStatus
    security_tier: SecurityTier
    runtime: AgentRuntime
    resources: ResourceLimits
    llm: LLMConfig
    tools: List[ToolConfig]
    networking: NetworkConfig
    autoscaling: AutoscalingConfig
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None


class Pagination(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class AgentListResponse(BaseModel):
    agents: List[Agent]
    pagination: Pagination


class Operation(BaseModel):
    id: UUID
    type: str
    status: OperationStatus
    created_at: datetime
    updated_at: datetime


class LogEntry(BaseModel):
    timestamp: datetime
    level: LogLevel
    message: str
    source: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LogStreamResponse(BaseModel):
    logs: List[LogEntry]
    next_cursor: Optional[str] = None


class ExecRequest(BaseModel):
    command: List[str]
    env: Dict[str, str] = Field(default_factory=dict)
    timeout_seconds: int = Field(30, ge=1, le=300)


class ExecResponse(BaseModel):
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int


class RetryPolicy(BaseModel):
    max_attempts: int = Field(3, ge=1)
    base_delay_seconds: int = Field(1, ge=1)
    max_delay_seconds: int = Field(300, ge=1)
    multiplier: float = Field(2.0, ge=1.0)
    jitter: float = Field(0.1, ge=0.0, le=1.0)
    retryable_errors: List[str] = Field(default_factory=list)


class Job(BaseModel):
    id: UUID
    type: str
    payload: Dict[str, Any]
    priority: int = 0
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    attempts: int = 0
    max_attempts: int = 3
    timeout_seconds: int = 300
    retry_policy: Optional[RetryPolicy] = None
    idempotency_key: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SubmitJobRequest(BaseModel):
    type: str
    payload: Dict[str, Any]
    priority: int = 0
    scheduled_at: Optional[datetime] = None
    timeout_seconds: int = Field(300, ge=1, le=86400)
    retry_policy: Optional[RetryPolicy] = None
    idempotency_key: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UsageBreakdown(BaseModel):
    agent_id: UUID
    agent_name: str
    event_type: str
    quantity: int
    unit_cost_usd: float
    total_cost_usd: float


class UsageResponse(BaseModel):
    period_start: str
    period_end: str
    total_cost_usd: float
    breakdown: List[UsageBreakdown]


class Template(BaseModel):
    id: str
    name: str
    description: str
    category: str
    runtime: AgentRuntime
    default_config: Dict[str, Any] = Field(default_factory=dict)


class TemplateListResponse(BaseModel):
    templates: List[Template]


class HealthCheck(BaseModel):
    name: str
    status: HealthCheckStatus
    message: Optional[str] = None


class HealthResponse(BaseModel):
    status: HealthStatus
    version: str
    timestamp: datetime
    checks: List[HealthCheck]


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)