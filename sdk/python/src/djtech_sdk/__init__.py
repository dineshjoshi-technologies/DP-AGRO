"""
DJ Tech Agent Runtime SDK for Python

A minimal SDK to create and manage AI agents on DJ Tech's platform.
Spin up your first agent in under 5 minutes.
"""

from .client import DJTechClient
from .models import (
    Agent,
    AgentRuntime,
    ResourceLimits,
    LLMConfig,
    ToolConfig,
    NetworkConfig,
    AutoscalingConfig,
    CreateAgentRequest,
    UpdateAgentRequest,
    Job,
    SubmitJobRequest,
    RetryPolicy,
    ExecRequest,
    ExecResponse,
    LogEntry,
    UsageBreakdown,
    Template,
)
from .exceptions import DJTechError, APIError, AuthenticationError, NotFoundError, ValidationError

__version__ = "1.0.0"

__all__ = [
    "DJTechClient",
    "Agent",
    "AgentRuntime",
    "ResourceLimits",
    "LLMConfig",
    "ToolConfig",
    "NetworkConfig",
    "AutoscalingConfig",
    "CreateAgentRequest",
    "UpdateAgentRequest",
    "Job",
    "SubmitJobRequest",
    "RetryPolicy",
    "ExecRequest",
    "ExecResponse",
    "LogEntry",
    "UsageBreakdown",
    "Template",
    "DJTechError",
    "APIError",
    "AuthenticationError",
    "NotFoundError",
    "ValidationError",
]