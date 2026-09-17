#!/usr/bin/env python3
"""
Agent with Tools - DJ Tech SDK Example

This example shows how to create an agent with built-in tools (web search, code execution)
and LLM configuration for AI-powered agents.

Prerequisites:
1. Set DJTECH_API_KEY environment variable
2. Install SDK: pip install djtech-sdk
"""

import asyncio
import os
from djtech_sdk import (
    DJTechClient,
    CreateAgentRequest,
    AgentRuntime,
    ResourceLimits,
    LLMConfig,
    ToolConfig,
    ToolType,
    NetworkConfig,
    ExecRequest,
)


async def main():
    api_key = os.environ.get("DJTECH_API_KEY")
    if not api_key:
        print("Error: DJTECH_API_KEY environment variable not set")
        return 1

    print("🤖 DJ Tech Agent with Tools Demo")
    print("=" * 40)

    async with DJTechClient(api_key=api_key) as client:
        # Create agent with tools and LLM config
        print("\n1. Creating agent with web search and code execution tools...")
        agent = await client.create_agent(
            CreateAgentRequest(
                name="research-assistant",
                description="Agent that can search the web and run code",
                security_tier="standard",
                runtime=AgentRuntime(
                    image="djtech/agent-python:3.11",
                    entrypoint=["python", "-m", "agent_main"],
                ),
                resources=ResourceLimits(
                    cpu="1000m",
                    memory="2Gi",
                    disk="1Gi",
                ),
                llm=LLMConfig(
                    default_model="gpt-4o-mini",
                    max_tokens_per_request=8192,
                    monthly_budget_usd=10.0,
                    allowed_models=["gpt-4o-mini", "gpt-4o", "claude-3.5-sonnet"],
                ),
                tools=[
                    ToolConfig(name="web_search", type=ToolType.BUILTIN),
                    ToolConfig(name="code_exec", type=ToolType.SANDBOXED, config={"language": "python", "timeout_seconds": 30}),
                ],
                networking=NetworkConfig(
                    egress_allowlist=[
                        "api.github.com",
                        "*.wikipedia.org",
                        "api.openai.com",
                        "api.anthropic.com",
                    ]
                ),
            )
        )
        print(f"   Created agent: {agent.id}")

        # Start agent
        print("\n2. Starting agent...")
        await client.start_agent(agent.id)
        print("   Agent started")

        # Wait for readiness
        print("   Waiting for agent to be ready...")
        await asyncio.sleep(5)

        # Test code execution tool
        print("\n3. Testing code execution tool...")
        result = await client.exec_in_agent(
            agent.id,
            ExecRequest(
                command=["python", "-c", """
import json
result = {"fibonacci": [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]}
print(json.dumps(result))
"""],
                timeout_seconds=10,
            )
        )
        print(f"   Result: {result.stdout.strip()}")

        # Test web search would require the agent to be running with the LLM
        # For now, let's just show how to submit a job for the agent to process
        print("\n4. Submitting a research job...")
        from djtech_sdk import SubmitJobRequest, RetryPolicy
        
        job = await client.submit_job(
            SubmitJobRequest(
                type="research_task",
                payload={
                    "prompt": "Research the latest developments in AI agent frameworks and summarize key trends",
                    "tools": ["web_search"],
                    "model": "gpt-4o-mini",
                },
                priority=10,
                retry_policy=RetryPolicy(max_attempts=3, base_delay_seconds=2),
            )
        )
        print(f"   Submitted job: {job.id}")
        print(f"   Status: {job.status}")

        # Poll for job completion
        print("   Polling for job completion...")
        for i in range(30):
            job = await client.get_job(job.id)
            print(f"   Attempt {i+1}: Status = {job.status}")
            if job.status in ["completed", "failed", "dead_letter"]:
                break
            await asyncio.sleep(2)
        
        if job.status == "completed":
            print(f"   Result: {job.result}")
        elif job.status == "failed":
            print(f"   Error: {job.error}")

        # Get usage
        print("\n5. Checking usage...")
        usage = await client.get_usage()
        print(f"   Total cost: ${usage.total_cost_usd:.4f}")
        for item in usage.breakdown:
            print(f"   {item.event_type}: {item.quantity} units = ${item.total_cost_usd:.4f}")

        # Stop and cleanup
        print("\n6. Stopping and cleaning up...")
        await client.stop_agent(agent.id)
        await client.delete_agent(agent.id)
        print("   Done")

    print("\n✅ Agent with Tools demo completed!")
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))