#!/usr/bin/env python3
"""
Hello Agent - Minimal DJ Tech SDK Example

This example creates a simple agent that prints "Hello, World!" and exits.
Run this after setting your DJTECH_API_KEY environment variable.

Prerequisites:
1. Set DJTECH_API_KEY environment variable
2. Install SDK: pip install djtech-sdk
"""

import asyncio
import os
from djtech_sdk import DJTechClient, CreateAgentRequest, AgentRuntime, ExecRequest


async def main():
    # Get API key from environment
    api_key = os.environ.get("DJTECH_API_KEY")
    if not api_key:
        print("Error: DJTECH_API_KEY environment variable not set")
        print("Get your API key at https://console.djtech.io")
        return 1
    
    print("🚀 DJ Tech Hello Agent Demo")
    print("=" * 40)
    
    async with DJTechClient(api_key=api_key) as client:
        # Check API health
        print("\n1. Checking API health...")
        health = await client.health_check()
        print(f"   Status: {health.status}")
        print(f"   Version: {health.version}")
        
        # Create agent
        print("\n2. Creating agent...")
        agent = await client.create_agent(
            CreateAgentRequest(
                name="hello-agent",
                description="Minimal hello world agent",
                runtime=AgentRuntime(
                    image="djtech/agent-python:3.11",
                    entrypoint=["python", "-m", "agent_main"],
                ),
            )
        )
        print(f"   Created agent: {agent.id}")
        print(f"   Name: {agent.name}")
        print(f"   Status: {agent.status}")
        
        # Start agent
        print("\n3. Starting agent...")
        operation = await client.start_agent(agent.id)
        print(f"   Start operation: {operation.id}")
        print(f"   Operation status: {operation.status}")
        
        # Wait a moment for agent to be ready
        print("   Waiting for agent to be ready...")
        await asyncio.sleep(3)
        
        # Execute hello world in agent sandbox
        print("\n4. Executing 'Hello, World!' in agent sandbox...")
        result = await client.exec_in_agent(
            agent.id,
            ExecRequest(
                command=["python", "-c", "print('Hello, World from DJ Tech agent!')"],
                timeout_seconds=10,
            )
        )
        print(f"   Exit code: {result.exit_code}")
        print(f"   Stdout: {result.stdout.strip()}")
        if result.stderr:
            print(f"   Stderr: {result.stderr.strip()}")
        print(f"   Duration: {result.duration_ms}ms")
        
        # Get agent logs
        print("\n5. Fetching agent logs...")
        logs = await client.get_agent_logs(agent.id, limit=10)
        for log in logs.logs:
            print(f"   [{log.level.upper()}] {log.source}: {log.message}")
        
        # Stop agent
        print("\n6. Stopping agent...")
        await client.stop_agent(agent.id)
        print("   Agent stopped successfully")
        
        # Clean up - delete agent
        print("\n7. Cleaning up (deleting agent)...")
        await client.delete_agent(agent.id)
        print("   Agent deleted")
    
    print("\n✅ Hello Agent demo completed successfully!")
    print("\nNext steps:")
    print("  - Visit https://console.djtech.io to see your agent")
    print("  - Try the job queue: client.submit_job(...)")
    print("  - Add tools: tools=[ToolConfig(name='web_search', type=ToolType.BUILTIN)]")
    print("  - Configure LLM: llm=LLMConfig(default_model='gpt-4o-mini')")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)