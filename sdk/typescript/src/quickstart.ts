/**
 * Quickstart helper for TypeScript
 */

import { DJTechClient } from './client';
import { CreateAgentRequest, Agent, AgentRuntime } from './models';

/**
 * Quickstart function to create and start an agent in one call.
 * 
 * Example:
 * ```typescript
 * import { createAgentQuickstart } from '@djtech/sdk';
 * 
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