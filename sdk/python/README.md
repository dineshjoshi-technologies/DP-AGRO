# DJ Tech Agent Runtime SDK for Python

A minimal SDK to create and manage AI agents on DJ Tech's platform. Spin up your first agent in under 5 minutes.

## Installation

```bash
pip install djtech-sdk
```

Or with Poetry:

```bash
poetry add djtech-sdk
```

## Quickstart

```python
import asyncio
from djtech_sdk import DJTechClient, CreateAgentRequest, AgentRuntime

async def main():
    # Initialize client with your API key
    client = DJTechClient(api_key="your-api-key")
    
    # Create an agent
    agent = await client.create_agent(
        CreateAgentRequest(
            name="hello-agent",
            description="My first DJ Tech agent",
            runtime=AgentRuntime(
                image="djtech/agent-python:3.11",
                entrypoint=["python", "-m", "agent_main"],
            ),
        )
    )
    
    print(f"Created agent: {agent.id}")
    
    # Start the agent
    operation = await client.start_agent(agent.id)
    print(f"Start operation: {operation.id}")
    
    # Execute a command in the agent's sandbox
    result = await client.exec_in_agent(agent.id, ExecRequest(
        command=["python", "-c", "print('Hello from agent!')"]
    ))
    print(f"Output: {result.stdout}")
    
    # Stop the agent
    await client.stop_agent(agent.id)
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## Even Faster: One-Liner Quickstart

```python
from djtech_sdk import create_agent_quickstart

agent = await create_agent_quickstart(
    api_key="your-api-key",
    agent_name="my-agent",
    entrypoint=["python", "-m", "my_agent"]
)
```

## Features

- **Agent Management**: Create, list, update, delete agents
- **Lifecycle Control**: Start, stop, restart agents
- **Sandbox Execution**: Run commands inside agent sandboxes
- **Job Queue**: Submit and monitor background jobs
- **Logging**: Stream agent logs in real-time
- **Billing**: Track usage and costs
- **Templates**: Browse pre-built agent templates
- **Async/Await**: Full async support with httpx
- **Type Safety**: Pydantic models for all API objects
- **Retries**: Automatic retry with exponential backoff
- **Error Handling**: Typed exceptions for all error cases

## Configuration

The client can be configured via environment variables or parameters:

```python
client = DJTechClient(
    api_key="your-api-key",           # or DJTECH_API_KEY env var
    base_url="https://api.djtech.io/v1",  # or DJTECH_BASE_URL env var
    timeout=30.0,                      # request timeout
    max_retries=3,                     # retry attempts
)
```

## API Reference

### DJTechClient

Main client class for interacting with the DJ Tech API.

#### Agent Management

- `create_agent(request: CreateAgentRequest) -> Agent`
- `list_agents(page=1, page_size=20, status=None, search=None) -> AgentListResponse`
- `get_agent(agent_id: UUID) -> Agent`
- `update_agent(agent_id: UUID, request: UpdateAgentRequest) -> Agent`
- `delete_agent(agent_id: UUID) -> None`
- `start_agent(agent_id: UUID) -> Operation`
- `stop_agent(agent_id: UUID, force=False, timeout_seconds=30) -> Operation`
- `get_agent_logs(agent_id, follow=False, since=None, limit=100) -> LogStreamResponse`
- `exec_in_agent(agent_id: UUID, request: ExecRequest) -> ExecResponse`

#### Job Management

- `submit_job(request: SubmitJobRequest) -> Job`
- `get_job(job_id: UUID) -> Job`
- `cancel_job(job_id: UUID) -> Job`
- `stream_job_events(job_id: UUID) -> AsyncIterator[Dict]`

#### Billing & Templates

- `get_usage(start_date=None, end_date=None, agent_id=None) -> UsageResponse`
- `list_templates() -> TemplateListResponse`

### Models

All API objects are Pydantic models with full type hints:

- `Agent`, `AgentRuntime`, `ResourceLimits`, `LLMConfig`
- `ToolConfig`, `NetworkConfig`, `AutoscalingConfig`
- `CreateAgentRequest`, `UpdateAgentRequest`, `StopAgentRequest`
- `Job`, `SubmitJobRequest`, `RetryPolicy`
- `ExecRequest`, `ExecResponse`, `LogEntry`
- `Operation`, `UsageBreakdown`, `Template`
- `HealthResponse`, `ErrorResponse`

### Exceptions

Typed exceptions for all error cases:

- `DJTechError` - Base exception
- `APIError` - Base API error
- `AuthenticationError` - 401 Unauthorized
- `AuthorizationError` - 403 Forbidden
- `NotFoundError` - 404 Not Found
- `ValidationError` - 400 Bad Request
- `ConflictError` - 409 Conflict
- `RateLimitError` - 429 Too Many Requests
- `ServerError` - 5xx Server Error
- `TimeoutError` - Request timeout
- `NetworkError` - Network connection error

## Examples

See the [examples/](examples/) directory for complete examples:

- `hello_agent.py` - Minimal agent creation and execution
- `job_processing.py` - Background job submission and monitoring
- `agent_with_tools.py` - Agent with custom tools and LLM config

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type check
mypy src/djtech_sdk

# Lint
ruff check src/djtech_sdk
```

## License

MIT License - see LICENSE file for details.

## Support

- Documentation: https://sdk.djtech.io/python
- Issues: https://github.com/djtech/sdk-python/issues
- Email: support@djtech.io