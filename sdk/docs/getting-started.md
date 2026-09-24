# DJ Tech SDK - Get Started in 5 Minutes

Welcome to DJ Tech! This guide will help you spin up your first AI agent in under 5 minutes.

## 🎯 What You'll Build

By the end of this guide, you'll have:
- A running AI agent on DJ Tech's secure sandboxed infrastructure
- The ability to execute code in the agent's isolated environment
- Access to built-in tools (web search, code execution)
- Real-time logs and monitoring

## 📋 Prerequisites

- **API Key**: Get yours at [console.djtech.io](https://console.djtech.io)
- **Python 3.10+** or **Node.js 18+**
- **5 minutes** of your time

---

## 🐍 Option 1: Python SDK (Recommended for ML/AI workloads)

### 1. Install the SDK

```bash
pip install djtech-sdk
```

### 2. Set Your API Key

```bash
export DJTECH_API_KEY="your-api-key-here"
```

### 3. Run the Hello Agent Example

```bash
# Download the example
curl -O https://raw.githubusercontent.com/djtech/sdk-python/main/examples/hello-agent/hello_agent.py

# Run it
python hello_agent.py
```

### 4. What Just Happened?

The script:
1. ✅ Connected to DJ Tech API
2. ✅ Created a sandboxed agent (`djtech/agent-python:3.11`)
3. ✅ Started the agent (cold start ~2 seconds)
4. ✅ Executed `print('Hello, World!')` inside the sandbox
5. ✅ Retrieved logs
6. ✅ Cleaned up (stopped & deleted agent)

### 5. Verify in Console

Visit [console.djtech.io](https://console.djtech.io) → **Agents** → You'll see `hello-agent` in your list.

---

## 🟦 Option 2: TypeScript/JavaScript SDK

### 1. Install the SDK

```bash
npm install @djtech/sdk
# or: yarn add @djtech/sdk
```

### 2. Set Your API Key

```bash
export DJTECH_API_KEY="your-api-key-here"
```

### 3. Create `hello-agent.ts`

```typescript
import { DJTechClient } from '@djtech/sdk';

const client = new DJTechClient({ apiKey: '[REDACTED:auth_header]' });

const agent = await client.createAgent({
  name: 'hello-agent-ts',
  runtime: { image: 'djtech/agent-python:3.11', entrypoint: ['python', '-m', 'agent_main'] },
});

await client.startAgent(agent.id);
await new Promise(r => setTimeout(r, 3000));

const result = await client.execInAgent(agent.id, {
  command: ['python', '-c', "print('Hello from TypeScript!')"],
});

console.log(result.stdout); // "Hello from TypeScript!"

await client.stopAgent(agent.id);
await client.deleteAgent(agent.id);
await client.close();
```

### 4. Run It

```bash
npx tsx hello-agent.ts
# Or compile first: npx tsc hello-agent.ts && node hello-agent.js
```

---

## 🛠️ Next Level: Agent with Tools

Want an agent that can **search the web** and **run code**? Here's how:

### Python

```python
from djtech_sdk import (
    DJTechClient, CreateAgentRequest, AgentRuntime,
    ResourceLimits, LLMConfig, ToolConfig, ToolType, NetworkConfig
)

async with DJTechClient() as client:
    agent = await client.create_agent(CreateAgentRequest(
        name="research-assistant",
        runtime=AgentRuntime(image="djtech/agent-python:3.11", entrypoint=["python", "-m", "agent_main"]),
        resources=ResourceLimits(cpu="1000m", memory="2Gi"),
        llm=LLMConfig(default_model="gpt-4o-mini", monthly_budget_usd=10.0),
        tools=[
            ToolConfig(name="web_search", type=ToolType.BUILTIN),
            ToolConfig(name="code_exec", type=ToolType.SANDBOXED, config={"language": "python", "timeout_seconds": 30}),
        ],
        networking=NetworkConfig(egress_allowlist=["api.github.com", "*.wikipedia.org", "api.openai.com"]),
    ))
    
    await client.start_agent(agent.id)
    # Now submit jobs that use web_search and code_exec!
    job = await client.submit_job(SubmitJobRequest(
        type="research_task",
        payload={"prompt": "Find the latest AI agent papers on arXiv", "tools": ["web_search"]},
    ))
```

### TypeScript

```typescript
import { DJTechClient, ToolType } from '@djtech/sdk';

const client = new DJTechClient({ apiKey: '[REDACTED:auth_header]' });

const agent = await client.createAgent({
  name: 'research-assistant',
  runtime: { image: 'djtech/agent-python:3.11', entrypoint: ['python', '-m', 'agent_main'] },
  resources: { cpu: '1000m', memory: '2Gi' },
  llm: { defaultModel: 'gpt-4o-mini', monthlyBudgetUsd: 10.0 },
  tools: [
    { name: 'web_search', type: ToolType.BUILTIN },
    { name: 'code_exec', type: ToolType.SANDBOXED, config: { language: 'python', timeoutSeconds: 30 } },
  ],
  networking: { egressAllowlist: ['api.github.com', '*.wikipedia.org', 'api.openai.com'] },
});

await client.startAgent(agent.id);
// Submit jobs with web_search and code_exec!
```

---

## 🔑 Key Concepts

| Concept | Description |
|---------|-------------|
| **Agent** | A sandboxed runtime for your AI workload |
| **Security Tier** | `standard` (gVisor), `high` (Kata VM), `system` (native) |
| **Tools** | Built-in capabilities: `web_search`, `code_exec`, MCP servers |
| **LLM Config** | Model selection, token limits, budget controls |
| **Job Queue** | Durable, retried, scheduled background work |
| **Sandbox Exec** | Run arbitrary commands in the agent's isolated environment |

---

## 📚 Common Patterns

### Run a One-Off Command
```python
result = await client.exec_in_agent(agent_id, ExecRequest(
    command=["python", "script.py", "--arg", "value"]
))
```

### Submit Background Job
```python
job = await client.submit_job(SubmitJobRequest(
    type="data_processing",
    payload={"input": "s3://bucket/data.csv", "output": "s3://bucket/results.parquet"},
    priority=10,
))
```

### Stream Logs in Real-Time
```python
async for log in client.stream_agent_logs(agent_id, follow=True):
    print(f"[{log.level}] {log.message}")
```

### Monitor Usage & Costs
```python
usage = await client.get_usage(start_date="2024-01-01", end_date="2024-01-31")
print(f"Total: ${usage.total_cost_usd:.2f}")
```

---

## 🔒 Security & Isolation

Every agent runs in a **gVisor sandbox** with:
- ✅ Syscall interception (no host kernel access)
- ✅ cgroups v2 resource limits (CPU, memory, disk, PIDs)
- ✅ Network namespace + eBPF egress allowlist
- ✅ LLM Gateway Proxy (token budgets, model allowlist, PII redaction)
- ✅ Read-only workspace + tmpfs secrets (no disk persistence)

---

## 💰 Pricing (Pay-Per-Use)

| Resource | Cost |
|----------|------|
| Sandbox seconds | $0.0001/sec |
| LLM tokens (input) | $5.00/1M (gpt-4o-mini) |
| LLM tokens (output) | $15.00/1M (gpt-4o-mini) |
| Tool calls | $0.001/call |
| Storage | $0.10/GB/month |

*Set `monthly_budget_usd` in LLMConfig to cap spending.*

---

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| `AuthenticationError` | Check `DJTECH_API_KEY` is set correctly |
| `NotFoundError` on agent | Agent may have been auto-deleted after 24h stopped |
| `TimeoutError` on start | Check network, try `timeout=60` in client config |
| Agent stuck in `pending` | Check quota limits in console |
| `exec_in_agent` fails | Ensure agent status is `running` |

---

## 📖 Full Documentation

- **Python SDK**: https://sdk.djtech.io/python
- **TypeScript SDK**: https://sdk.djtech.io/typescript
- **API Reference**: https://api.djtech.io/docs
- **Examples Repo**: https://github.com/djtech/sdk-examples

---

## 🤝 Get Help

- **Discord**: https://discord.gg/djtech
- **GitHub Issues**: https://github.com/djtech/sdk-python/issues
- **Email**: support@djtech.io

---

## 🎉 You're Ready!

You now have everything to start building with DJ Tech. 

**What will you build first?**
- A research agent that summarizes papers?
- A code review bot for your repos?
- A data processing pipeline?
- Something entirely new?

Happy building! 🚀

---

*The DJ Tech Team*