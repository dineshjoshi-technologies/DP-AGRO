/**
 * Main client for DJ Tech Agent Runtime API
 */

import axios, { AxiosInstance, AxiosError, AxiosRequestConfig, InternalAxiosRequestConfig } from 'axios';
import axiosRetry from 'axios-retry';

import {
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
  AgentRuntime,
  ResourceLimits,
  LLMConfig,
} from './models';
import {
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
  mapHttpError,
} from './exceptions';

export interface DJTechClientConfig {
  apiKey?: string;
  baseURL?: string;
  timeout?: number;
  maxRetries?: number;
}

/**
 * DJ Tech Agent Runtime API Client
 * 
 * Example:
 * ```typescript
 * const client = new DJTechClient({ apiKey: 'your-api-key' });
 * const agent = await client.createAgent({
 *   name: 'my-agent',
 *   runtime: { image: 'djtech/agent-python:3.11', entrypoint: ['python', '-m', 'agent_main'] }
 * });
 * await client.startAgent(agent.id);
 * ```
 */
export class DJTechClient {
  private client: AxiosInstance;
  private baseURL: string;
  private timeout: number;
  private maxRetries: number;

  constructor(config: DJTechClientConfig = {}) {
    this.baseURL = config.baseURL || process.env['DJTECH_BASE_URL'] || 'https://api.djtech.io/v1';
    this.timeout = config.timeout || 30000;
    this.maxRetries = config.maxRetries || 3;

    const apiKey = config.apiKey || process.env['DJTECH_API_KEY'];
    if (!apiKey) {
      throw new Error('API key is required. Set DJTECH_API_KEY env var or pass apiKey parameter.');
    }

    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: this.timeout,
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
        'User-Agent': 'djtech-sdk-typescript/1.0.0',
      },
    });

    // Configure retries
    axiosRetry(this.client, {
      retries: this.maxRetries,
      retryDelay: axiosRetry.exponentialDelay,
      retryCondition: (error: AxiosError) => {
        // Retry on network errors or 5xx errors
        if (axiosRetry.isNetworkOrIdempotentRequestError(error)) return true;
        if (error.response && error.response.status >= 500) return true;
        return false;
      },
    });

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response) {
          const data = error.response.data as ErrorResponse | undefined;
          const message = data?.message || `HTTP ${error.response.status}: ${error.message}`;
          const code = data?.code;
          const details = data?.details || {};
          
          throw mapHttpError(error.response.status, message, code, details);
        } else if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
          throw new TimeoutError(`Request timed out: ${error.message}`);
        } else {
          throw new NetworkError(`Network error: ${error.message}`);
        }
      }
    );
  }

  /**
   * Close the client (cleanup)
   */
  async close(): Promise<void> {
    // Axios doesn't need explicit close, but we provide this for consistency
  }

  // Health check
  async healthCheck(): Promise<HealthResponse> {
    const response = await this.client.get<HealthResponse>('/health');
    return response.data;
  }

  // Agent management
  async createAgent(request: CreateAgentRequest): Promise<Agent> {
    const response = await this.client.post<Agent>('/agents', request);
    return response.data;
  }

  async listAgents(params?: {
    page?: number;
    page_size?: number;
    status?: string;
    search?: string;
  }): Promise<AgentListResponse> {
    const response = await this.client.get<AgentListResponse>('/agents', { params });
    return response.data;
  }

  async getAgent(agentId: string): Promise<Agent> {
    const response = await this.client.get<Agent>(`/agents/${agentId}`);
    return response.data;
  }

  async updateAgent(agentId: string, request: UpdateAgentRequest): Promise<Agent> {
    const response = await this.client.patch<Agent>(`/agents/${agentId}`, request);
    return response.data;
  }

  async deleteAgent(agentId: string): Promise<void> {
    await this.client.delete(`/agents/${agentId}`);
  }

  async startAgent(agentId: string): Promise<Operation> {
    const response = await this.client.post<Operation>(`/agents/${agentId}/start`);
    return response.data;
  }

  async stopAgent(agentId: string, force = false, timeoutSeconds = 30): Promise<Operation> {
    const request: StopAgentRequest = { force, timeout_seconds: timeoutSeconds };
    const response = await this.client.post<Operation>(`/agents/${agentId}/stop`, request);
    return response.data;
  }

  async getAgentLogs(
    agentId: string,
    options?: {
      follow?: boolean;
      since?: string;
      limit?: number;
    }
  ): Promise<LogStreamResponse> {
    const params = {
      follow: options?.follow ? 'true' : 'false',
      limit: options?.limit || 100,
      ...(options?.since && { since: options.since }),
    };
    const response = await this.client.get<LogStreamResponse>(`/agents/${agentId}/logs`, { params });
    return response.data;
  }

  async execInAgent(agentId: string, request: ExecRequest): Promise<ExecResponse> {
    const response = await this.client.post<ExecResponse>(`/agents/${agentId}/exec`, request);
    return response.data;
  }

  // Job management
  async submitJob(request: SubmitJobRequest): Promise<Job> {
    const response = await this.client.post<Job>('/jobs', request);
    return response.data;
  }

  async getJob(jobId: string): Promise<Job> {
    const response = await this.client.get<Job>(`/jobs/${jobId}`);
    return response.data;
  }

  async cancelJob(jobId: string): Promise<Job> {
    const response = await this.client.post<Job>(`/jobs/${jobId}/cancel`);
    return response.data;
  }

  async *streamJobEvents(jobId: string): AsyncGenerator<Record<string, unknown>, void, unknown> {
    const response = await this.client.get(`/jobs/${jobId}/events`, {
      responseType: 'stream',
      headers: { Accept: 'text/event-stream' },
    });

    // Parse SSE stream
    for await (const chunk of response.data) {
      const lines = chunk.toString().split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            yield JSON.parse(line.slice(6));
          } catch {
            // Ignore parse errors
          }
        }
      }
    }
  }

  // Billing
  async getUsage(params?: {
    start_date?: string;
    end_date?: string;
    agent_id?: string;
  }): Promise<UsageResponse> {
    const response = await this.client.get<UsageResponse>('/billing/usage', { params });
    return response.data;
  }

  // Templates
  async listTemplates(): Promise<TemplateListResponse> {
    const response = await this.client.get<TemplateListResponse>('/templates');
    return response.data;
  }
}

/**
 * Quickstart function to create and start an agent in one call.
 * 
 * Example:
 * ```typescript
 * const agent = await createAgentQuickstart({
 *   apiKey: 'your-key',
 *   agentName: 'hello-agent',
 *   entrypoint: ['python', '-m', 'my_agent']
 * });
 * ```
 */
export async function createAgentQuickstart(config: {
  apiKey: string;
  agentName: string;
  image?: string;
  entrypoint?: string[];
  description?: string;
  baseURL?: string;
}): Promise<Agent> {
  const client = new DJTechClient({
    apiKey: config.apiKey,
    baseURL: config.baseURL,
  });

  try {
    const request: CreateAgentRequest = {
      name: config.agentName,
      description: config.description,
      runtime: {
        image: config.image || 'djtech/agent-python:3.11',
        entrypoint: config.entrypoint || ['python', '-m', 'agent_main'],
      },
    };
    
    const agent = await client.createAgent(request);
    await client.startAgent(agent.id);
    return agent;
  } finally {
    await client.close();
  }
}

// Export a default instance creator for convenience
export function createClient(config: DJTechClientConfig = {}): DJTechClient {
  return new DJTechClient(config);
}

// Default export
export default DJTechClient;