"""
Main client for DJ Tech Agent Runtime API
"""

import os
import asyncio
from typing import Any, AsyncIterator, Dict, List, Optional
from uuid import UUID

import httpx
from pydantic import BaseModel

from .models import (
    Agent,
    AgentListResponse,
    CreateAgentRequest,
    UpdateAgentRequest,
    StopAgentRequest,
    Job,
    SubmitJobRequest,
    ExecRequest,
    ExecResponse,
    LogEntry,
    LogStreamResponse,
    Operation,
    TemplateListResponse,
    UsageResponse,
    HealthResponse,
    ErrorResponse,
)
from .exceptions import (
    DJTechError,
    APIError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ValidationError,
    ConflictError,
    RateLimitError,
    ServerError,
    TimeoutError,
    NetworkError,
    map_http_error,
)


class DJTechClient:
    """
    DJ Tech Agent Runtime API Client
    
    Example:
        client = DJTechClient(api_key="your-api-key")
        agent = client.create_agent(
            name="my-agent",
            runtime={"image": "djtech/agent-python:3.11", "entrypoint": ["python", "-m", "agent_main"]}
        )
        client.start_agent(agent.id)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.djtech.io/v1",
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """
        Initialize the DJ Tech client.
        
        Args:
            api_key: API key for authentication. Can also be set via DJTECH_API_KEY env var.
            base_url: Base URL for the API.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retries for failed requests.
        """
        self.api_key = api_key or os.environ.get("DJTECH_API_KEY")
        if not self.api_key:
            raise ValueError("API key is required. Set DJTECH_API_KEY env var or pass api_key parameter.")
        
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": f"djtech-sdk-python/1.0.0",
            },
        )
    
    async def __aenter__(self) -> "DJTechClient":
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
    
    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
    
    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Handle HTTP response and raise appropriate exceptions."""
        if response.is_success:
            if response.status_code == 204:
                return {}
            return response.json()
        
        try:
            error_data = response.json()
            message = error_data.get("message", f"HTTP {response.status_code}")
            code = error_data.get("code")
            details = error_data.get("details", {})
        except Exception:
            message = f"HTTP {response.status_code}: {response.text}"
            code = None
            details = {}
        
        raise map_http_error(response.status_code, message, code, details)
    
    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make an HTTP request with retries."""
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.request(
                    method=method,
                    url=path,
                    params=params,
                    json=json,
                )
                return self._handle_response(response)
            
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_error = NetworkError(f"Network error: {e}")
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
            
            except APIError as e:
                if e.status_code >= 500 and attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
        
        raise last_error or DJTechError("Max retries exceeded")
    
    # Health check
    async def health_check(self) -> HealthResponse:
        """Check API health status."""
        data = await self._request("GET", "/health")
        return HealthResponse(**data)
    
    # Agent management
    async def create_agent(self, request: CreateAgentRequest) -> Agent:
        """Create a new agent."""
        data = await self._request("POST", "/agents", json=request.model_dump(exclude_none=True))
        return Agent(**data)
    
    async def list_agents(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> AgentListResponse:
        """List agents with pagination and filters."""
        params = {"page": page, "page_size": page_size}
        if status:
            params["status"] = status
        if search:
            params["search"] = search
        
        data = await self._request("GET", "/agents", params=params)
        return AgentListResponse(**data)
    
    async def get_agent(self, agent_id: UUID) -> Agent:
        """Get agent by ID."""
        data = await self._request("GET", f"/agents/{agent_id}")
        return Agent(**data)
    
    async def update_agent(self, agent_id: UUID, request: UpdateAgentRequest) -> Agent:
        """Update agent configuration."""
        data = await self._request("PATCH", f"/agents/{agent_id}", json=request.model_dump(exclude_none=True))
        return Agent(**data)
    
    async def delete_agent(self, agent_id: UUID) -> None:
        """Delete an agent."""
        await self._request("DELETE", f"/agents/{agent_id}")
    
    async def start_agent(self, agent_id: UUID) -> Operation:
        """Start an agent."""
        data = await self._request("POST", f"/agents/{agent_id}/start")
        return Operation(**data)
    
    async def stop_agent(self, agent_id: UUID, force: bool = False, timeout_seconds: int = 30) -> Operation:
        """Stop an agent."""
        request = StopAgentRequest(force=force, timeout_seconds=timeout_seconds)
        data = await self._request("POST", f"/agents/{agent_id}/stop", json=request.model_dump())
        return Operation(**data)
    
    async def get_agent_logs(
        self,
        agent_id: UUID,
        follow: bool = False,
        since: Optional[str] = None,
        limit: int = 100,
    ) -> LogStreamResponse:
        """Get agent logs."""
        params = {"follow": str(follow).lower(), "limit": limit}
        if since:
            params["since"] = since
        
        data = await self._request("GET", f"/agents/{agent_id}/logs", params=params)
        return LogStreamResponse(**data)
    
    async def exec_in_agent(self, agent_id: UUID, request: ExecRequest) -> ExecResponse:
        """Execute a command in the agent's sandbox."""
        data = await self._request("POST", f"/agents/{agent_id}/exec", json=request.model_dump())
        return ExecResponse(**data)
    
    # Job management
    async def submit_job(self, request: SubmitJobRequest) -> Job:
        """Submit a job for execution."""
        data = await self._request("POST", "/jobs", json=request.model_dump(exclude_none=True))
        return Job(**data)
    
    async def get_job(self, job_id: UUID) -> Job:
        """Get job status and result."""
        data = await self._request("GET", f"/jobs/{job_id}")
        return Job(**data)
    
    async def cancel_job(self, job_id: UUID) -> Job:
        """Cancel a running job."""
        data = await self._request("POST", f"/jobs/{job_id}/cancel")
        return Job(**data)
    
    async def stream_job_events(self, job_id: UUID) -> AsyncIterator[Dict[str, Any]]:
        """Stream job events via SSE."""
        async with self._client.stream("GET", f"/jobs/{job_id}/events") as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    import json
                    yield json.loads(line[6:])
    
    # Billing
    async def get_usage(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        agent_id: Optional[UUID] = None,
    ) -> UsageResponse:
        """Get usage and billing information."""
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if agent_id:
            params["agent_id"] = str(agent_id)
        
        data = await self._request("GET", "/billing/usage", params=params)
        return UsageResponse(**data)
    
    # Templates
    async def list_templates(self) -> TemplateListResponse:
        """List available agent templates."""
        data = await self._request("GET", "/templates")
        return TemplateListResponse(**data)


# Convenience function for quick setup
async def create_agent_quickstart(
    api_key: str,
    agent_name: str,
    image: str = "djtech/agent-python:3.11",
    entrypoint: Optional[List[str]] = None,
    description: Optional[str] = None,
) -> Agent:
    """
    Quickstart function to create and start an agent in one call.
    
    Example:
        agent = await create_agent_quickstart(
            api_key="your-key",
            agent_name="hello-agent",
            entrypoint=["python", "-m", "my_agent"]
        )
    """
    async with DJTechClient(api_key=api_key) as client:
        request = CreateAgentRequest(
            name=agent_name,
            description=description,
            runtime=AgentRuntime(
                image=image,
                entrypoint=entrypoint or ["python", "-m", "agent_main"],
            ),
        )
        agent = await client.create_agent(request)
        await client.start_agent(agent.id)
        return agent