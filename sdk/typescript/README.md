# DJ Tech Agent Runtime SDK for TypeScript

A minimal SDK to create and manage AI agents on DJ Tech's platform. Spin up your first agent in under 5 minutes.

## Installation

```bash
npm install @djtech/sdk
```

Or with Yarn:

```bash
yarn add @djtech/sdk
```

Or with pnpm:

```bash
pnpm add @djtech/sdk
```

## Quickstart

```typescript
import { DJTechClient, CreateAgentRequest } from '@djtech/sdk';

async function main() {
  // Initialize client with your API key
  const client = new DJTechClient({ apiKey: 'your-api-key' });
  
  // Create an agent
  const agent = await client.createAgent({
    name: 'hello-agent',
    description: 'My first DJ Tech agent',
    runtime: {
      image: 'djtech/agent-python:3.11',
      entrypoint: ['python', '-m', 'agent_main'],
    },
  });
  
  console.log(`Created agent: ${agent.id}`);
  
  // Start the agent
  const operation = await client.startAgent(agent.id);
  console.log(`Start operation: ${operation.id}`);
  
  // Execute a command in the agent's sandbox
  const result = await client.execInAgent(agent.id, {
    command: ['python', '-c', "print('Hello from agent!')"],
  });
  console.log(`Output: ${result.stdout}`);
  
  // Stop the agent
  await client.stopAgent(agent.id);
  
  await client.close();
}

main().catch(console.error);
```

## Even Faster: One-Liner Quickstart

```typescript
import { createAgentQuickstart } from '@djtech/sdk';

const agent = await createAgentQuickstart({
  apiKey: 'your-api-key',
  agentName: 'my-agent',
  entrypoint: ['python', '-m', 'my_agent'],
});
```

## Features

- **Agent Management**: Create, list, update, delete agents
- **Lifecycle Control**: Start, stop, restart agents
- **Sandbox Execution**: Run commands inside agent sandboxes
- **Job Queue**: Submit and monitor background jobs
- **Logging**: Stream agent logs in real-time
- **Billing**: Track usage and costs
- **Templates**: Browse pre-built agent templates
- **Async/Await**: Full async support with axios
- **Type Safety**: TypeScript types for all API objects
- **Retries**: Automatic retry with exponential backoff
- **Error Handling**: Typed exceptions for all error cases
- **SSE Support**: Stream job events via Server-Sent Events

## Configuration

The client can be configured via environment variables or parameters:

```typescript
const client = new DJTechClient({
  apiKey: 'your-api-key',                    // or DJTECH_API_KEY env var
  baseURL: 'https://api.djtech.io/v1',       // or DJTECH_BASE_URL env var
  timeout: 30000,                            // request timeout in ms
  maxRetries: 3,                             // retry attempts
});
```

## API Reference

### DJTechClient

Main client class for interacting with the DJ Tech API.

#### Agent Management

- `createAgent(request: CreateAgentRequest): Promise<Agent>`
- `listAgents(params?: { page, page_size, status, search }): Promise<AgentListResponse>`
- `getAgent(agentId: string): Promise<Agent>`
- `updateAgent(agentId: string, request: UpdateAgentRequest): Promise<Agent>`
- `deleteAgent(agentId: string): Promise<void>`
- `startAgent(agentId: string): Promise<Operation>`
- `stopAgent(agentId: string, force?: boolean, timeoutSeconds?: number): Promise<Operation>`
- `getAgentLogs(agentId: string, options?: { follow, since, limit }): Promise<LogStreamResponse>`
- `execInAgent(agentId: string, request: ExecRequest): Promise<ExecResponse>`

#### Job Management

- `submitJob(request: SubmitJobRequest): Promise<Job>`
- `getJob(jobId: string): Promise<Job>`
- `cancelJob(jobId: string): Promise<Job>`
- `streamJobEvents(jobId: string): AsyncGenerator<Record<string, unknown>>`

#### Billing & Templates

- `getUsage(params?: { start_date, end_date, agent_id }): Promise<UsageResponse>`
- `listTemplates(): Promise<TemplateListResponse>`

### Models

All API objects are TypeScript interfaces with full type safety:

- `Agent`, `AgentRuntime`, `ResourceLimits`, `LLMConfig`
- `ToolConfig`, `NetworkConfig`, `AutoscalingConfig`
- `CreateAgentRequest`, `UpdateAgentRequest`, `StopAgentRequest`
- `Job`, `SubmitJobRequest`, `RetryPolicy`
- `ExecRequest`, `ExecResponse`, `LogEntry`
- `Operation`, `UsageBreakdown`, `Template`
- `HealthResponse`, `ErrorResponse`

### Enums

- `SecurityTier`: `STANDARD`, `HIGH`, `SYSTEM`
- `AgentStatus`: `PENDING`, `RUNNING`, `STOPPED`, `FAILED`, `DELETED`
- `JobStatus`: `PENDING`, `SCHEDULED`, `PROCESSING`, `COMPLETED`, `FAILED`, `DEAD_LETTER`, `CANCELLED`
- `ToolType`: `BUILTIN`, `SANDBOXED`, `MCP`
- `LogLevel`: `DEBUG`, `INFO`, `WARN`, `ERROR`
- `OperationStatus`: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`

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

- `hello-agent.ts` - Minimal agent creation and execution
- `job-processing.ts` - Background job submission and monitoring
- `agent-with-tools.ts` - Agent with custom tools and LLM config

## Development

```bash
# Install dependencies
npm install

# Build
npm run build

# Run tests
npm test

# Type check
npm run typecheck

# Lint
npm run lint
```

## License

MIT License - see LICENSE file for details.

## Support

- Documentation: https://sdk.djtech.io/typescript
- Issues: https://github.com/djtech/sdk-typescript/issues
- Email: support@djtech.io