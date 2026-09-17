"""Tests for DJ Tech SDK models"""
import pytest
from uuid import UUID
from datetime import datetime

from djtech_sdk.models import (
    AgentRuntime,
    ResourceLimits,
    LLMConfig,
    ToolConfig,
    NetworkConfig,
    AutoscalingConfig,
    CreateAgentRequest,
    UpdateAgentRequest,
    StopAgentRequest,
    Agent,
    AgentStatus,
    SecurityTier,
    ToolType,
    Job,
    JobStatus,
    SubmitJobRequest,
    RetryPolicy,
    ExecRequest,
    ExecResponse,
    LogEntry,
    LogLevel,
    UsageResponse,
    UsageBreakdown,
    Template,
    HealthResponse,
    HealthStatus,
    HealthCheck,
    HealthCheckStatus,
)


class TestAgentRuntime:
    def test_defaults(self):
        runtime = AgentRuntime(image="test:latest")
        assert runtime.image == "test:latest"
        assert runtime.entrypoint == []
        assert runtime.env == {}

    def test_with_values(self):
        runtime = AgentRuntime(
            image="djtech/agent-python:3.11",
            entrypoint=["python", "-m", "agent_main"],
            env={"KEY": "value"}
        )
        assert runtime.image == "djtech/agent-python:3.11"
        assert runtime.entrypoint == ["python", "-m", "agent_main"]
        assert runtime.env == {"KEY": "value"}


class TestResourceLimits:
    def test_defaults(self):
        limits = ResourceLimits()
        assert limits.cpu == "1000m"
        assert limits.memory == "2Gi"
        assert limits.disk == "1Gi"
        assert limits.max_execution_time == "24h"

    def test_custom(self):
        limits = ResourceLimits(cpu="2000m", memory="4Gi", disk="5Gi", max_execution_time="48h")
        assert limits.cpu == "2000m"
        assert limits.memory == "4Gi"


class TestLLMConfig:
    def test_defaults(self):
        llm = LLMConfig()
        assert llm.default_model == "gpt-4o-mini"
        assert llm.max_tokens_per_request == 8192
        assert llm.monthly_budget_usd == 50.0
        assert "gpt-4o-mini" in llm.allowed_models


class TestToolConfig:
    def test_defaults(self):
        tool = ToolConfig(name="web_search")
        assert tool.name == "web_search"
        assert tool.type == ToolType.BUILTIN
        assert tool.config == {}

    def test_sandboxed(self):
        tool = ToolConfig(name="code_exec", type=ToolType.SANDBOXED, config={"language": "python"})
        assert tool.type == ToolType.SANDBOXED
        assert tool.config == {"language": "python"}


class TestNetworkConfig:
    def test_defaults(self):
        net = NetworkConfig()
        assert net.egress_allowlist == []

    def test_with_allowlist(self):
        net = NetworkConfig(egress_allowlist=["api.github.com", "*.wikipedia.org"])
        assert net.egress_allowlist == ["api.github.com", "*.wikipedia.org"]


class TestAutoscalingConfig:
    def test_defaults(self):
        auto = AutoscalingConfig()
        assert auto.min_replicas == 0
        assert auto.max_replicas == 10
        assert auto.scale_up_delay_seconds == 30


class TestCreateAgentRequest:
    def test_minimal(self):
        request = CreateAgentRequest(
            name="test-agent",
            runtime=AgentRuntime(image="test:latest")
        )
        assert request.name == "test-agent"
        assert request.security_tier == SecurityTier.STANDARD
        assert request.tools == []

    def test_full(self):
        request = CreateAgentRequest(
            name="test-agent",
            description="Test agent",
            security_tier=SecurityTier.HIGH,
            runtime=AgentRuntime(image="test:latest", entrypoint=["python", "main.py"]),
            resources=ResourceLimits(cpu="2000m"),
            llm=LLMConfig(default_model="gpt-4o"),
            tools=[ToolConfig(name="web_search")],
            networking=NetworkConfig(egress_allowlist=["api.openai.com"]),
            autoscaling=AutoscalingConfig(min_replicas=1),
        )
        assert request.security_tier == SecurityTier.HIGH
        assert len(request.tools) == 1


class TestUpdateAgentRequest:
    def test_empty(self):
        request = UpdateAgentRequest()
        assert request.description is None
        assert request.tools == []

    def test_with_updates(self):
        request = UpdateAgentRequest(
            description="Updated",
            tools=[ToolConfig(name="code_exec", type=ToolType.SANDBOXED)]
        )
        assert request.description == "Updated"
        assert len(request.tools) == 1


class TestStopAgentRequest:
    def test_defaults(self):
        request = StopAgentRequest()
        assert request.force is False
        assert request.timeout_seconds == 30

    def test_custom(self):
        request = StopAgentRequest(force=True, timeout_seconds=60)
        assert request.force is True
        assert request.timeout_seconds == 60


class TestAgent:
    def test_creation(self):
        now = datetime.now()
        agent = Agent(
            id=UUID("12345678-1234-5678-1234-567812345678"),
            name="test-agent",
            description="Test",
            status=AgentStatus.RUNNING,
            security_tier=SecurityTier.STANDARD,
            runtime=AgentRuntime(image="test:latest"),
            resources=ResourceLimits(),
            llm=LLMConfig(),
            tools=[],
            networking=NetworkConfig(),
            autoscaling=AutoscalingConfig(),
            created_at=now,
            updated_at=now,
        )
        assert agent.name == "test-agent"
        assert agent.status == AgentStatus.RUNNING


class TestJob:
    def test_creation(self):
        now = datetime.now()
        job = Job(
            id=UUID("12345678-1234-5678-1234-567812345678"),
            type="test_job",
            payload={"key": "value"},
            status=JobStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        assert job.type == "test_job"
        assert job.status == JobStatus.PENDING


class TestSubmitJobRequest:
    def test_minimal(self):
        request = SubmitJobRequest(type="test", payload={})
        assert request.type == "test"
        assert request.priority == 0
        assert request.timeout_seconds == 300

    def test_with_options(self):
        request = SubmitJobRequest(
            type="test",
            payload={"data": "value"},
            priority=10,
            timeout_seconds=600,
            retry_policy=RetryPolicy(max_attempts=5),
        )
        assert request.priority == 10
        assert request.timeout_seconds == 600
        assert request.retry_policy.max_attempts == 5


class TestRetryPolicy:
    def test_defaults(self):
        policy = RetryPolicy()
        assert policy.max_attempts == 3
        assert policy.base_delay_seconds == 1
        assert policy.max_delay_seconds == 300
        assert policy.multiplier == 2.0
        assert policy.jitter == 0.1


class TestExecRequest:
    def test_minimal(self):
        request = ExecRequest(command=["echo", "hello"])
        assert request.command == ["echo", "hello"]
        assert request.timeout_seconds == 30

    def test_with_env(self):
        request = ExecRequest(
            command=["python", "script.py"],
            env={"ENV_VAR": "value"},
            timeout_seconds=60
        )
        assert request.env == {"ENV_VAR": "value"}
        assert request.timeout_seconds == 60


class TestExecResponse:
    def test_creation(self):
        response = ExecResponse(
            exit_code=0,
            stdout="hello\n",
            stderr="",
            duration_ms=100
        )
        assert response.exit_code == 0
        assert response.stdout == "hello\n"
        assert response.duration_ms == 100


class TestLogEntry:
    def test_creation(self):
        now = datetime.now()
        log = LogEntry(
            timestamp=now,
            level=LogLevel.INFO,
            message="Test message",
            source="agent",
            metadata={"key": "value"}
        )
        assert log.level == LogLevel.INFO
        assert log.message == "Test message"


class TestUsageBreakdown:
    def test_creation(self):
        breakdown = UsageBreakdown(
            agent_id=UUID("12345678-1234-5678-1234-567812345678"),
            agent_name="test-agent",
            event_type="llm_tokens",
            quantity=1000,
            unit_cost_usd=0.005,
            total_cost_usd=5.0
        )
        assert breakdown.event_type == "llm_tokens"
        assert breakdown.total_cost_usd == 5.0


class TestUsageResponse:
    def test_creation(self):
        now = datetime.now()
        response = UsageResponse(
            period_start="2024-01-01",
            period_end="2024-01-31",
            total_cost_usd=10.0,
            breakdown=[]
        )
        assert response.total_cost_usd == 10.0


class TestTemplate:
    def test_creation(self):
        template = Template(
            id="template-1",
            name="Python Agent",
            description="A Python agent template",
            category="general",
            runtime=AgentRuntime(image="djtech/agent-python:3.11"),
        )
        assert template.name == "Python Agent"


class TestHealthResponse:
    def test_creation(self):
        response = HealthResponse(
            status=HealthStatus.HEALTHY,
            version="1.0.0",
            timestamp=datetime.now(),
            checks=[
                HealthCheck(name="database", status=HealthCheckStatus.PASS),
                HealthCheck(name="cache", status=HealthCheckStatus.PASS, message="OK"),
            ]
        )
        assert response.status == HealthStatus.HEALTHY
        assert len(response.checks) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])