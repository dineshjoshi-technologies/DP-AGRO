#!/usr/bin/env node
/**
 * Hello Agent - Minimal DJ Tech SDK Example (TypeScript)
 * 
 * This example creates a simple agent that prints "Hello, World!" and exits.
 * Run this after setting your DJTECH_API_KEY environment variable.
 * 
 * Prerequisites:
 * 1. Set DJTECH_API_KEY environment variable
 * 2. Install SDK: npm install @djtech/sdk
 * 3. Compile: npx tsc hello-agent.ts (or run with tsx: npx tsx hello-agent.ts)
 */

import { DJTechClient, CreateAgentRequest, AgentRuntime, ExecRequest } from '@djtech/sdk';

async function main(): Promise<number> {
  // Get API key from environment
  const apiKey = process.env.DJTECH_API_KEY;
  if (!apiKey) {
    console.error('Error: DJTECH_API_KEY environment variable not set');
    console.error('Get your API key at https://console.djtech.io');
    return 1;
  }

  console.log('🚀 DJ Tech Hello Agent Demo (TypeScript)');
  console.log('='.repeat(40));

  const client = new DJTechClient({ apiKey });

  try {
    // Check API health
    console.log('\n1. Checking API health...');
    const health = await client.healthCheck();
    console.log(`   Status: ${health.status}`);
    console.log(`   Version: ${health.version}`);

    // Create agent
    console.log('\n2. Creating agent...');
    const agent = await client.createAgent({
      name: 'hello-agent-ts',
      description: 'Minimal hello world agent (TypeScript)',
      runtime: {
        image: 'djtech/agent-python:3.11',
        entrypoint: ['python', '-m', 'agent_main'],
      },
    } as CreateAgentRequest);
    console.log(`   Created agent: ${agent.id}`);
    console.log(`   Name: ${agent.name}`);
    console.log(`   Status: ${agent.status}`);

    // Start agent
    console.log('\n3. Starting agent...');
    const operation = await client.startAgent(agent.id);
    console.log(`   Start operation: ${operation.id}`);
    console.log(`   Operation status: ${operation.status}`);

    // Wait a moment for agent to be ready
    console.log('   Waiting for agent to be ready...');
    await new Promise(resolve => setTimeout(resolve, 3000));

    // Execute hello world in agent sandbox
    console.log("\n4. Executing 'Hello, World!' in agent sandbox...");
    const result = await client.execInAgent(agent.id, {
      command: ['python', '-c', "print('Hello, World from DJ Tech agent (TypeScript)!')"],
      timeoutSeconds: 10,
    } as ExecRequest);
    console.log(`   Exit code: ${result.exit_code}`);
    console.log(`   Stdout: ${result.stdout.trim()}`);
    if (result.stderr) {
      console.log(`   Stderr: ${result.stderr.trim()}`);
    }
    console.log(`   Duration: ${result.duration_ms}ms`);

    // Get agent logs
    console.log('\n5. Fetching agent logs...');
    const logs = await client.getAgentLogs(agent.id, { limit: 10 });
    for (const log of logs.logs) {
      console.log(`   [${log.level.toUpperCase()}] ${log.source}: ${log.message}`);
    }

    // Stop agent
    console.log('\n6. Stopping agent...');
    await client.stopAgent(agent.id);
    console.log('   Agent stopped successfully');

    // Clean up - delete agent
    console.log('\n7. Cleaning up (deleting agent)...');
    await client.deleteAgent(agent.id);
    console.log('   Agent deleted');

    console.log('\n✅ Hello Agent demo completed successfully!');
    console.log('\nNext steps:');
    console.log('  - Visit https://console.djtech.io to see your agent');
    console.log('  - Try the job queue: client.submitJob(...)');
    console.log('  - Add tools: tools=[{name: "web_search", type: "builtin"}]');
    console.log('  - Configure LLM: llm={defaultModel: "gpt-4o-mini"}');
    return 0;
  } catch (error) {
    console.error('\n❌ Error:', error);
    return 1;
  } finally {
    await client.close();
  }
}

// Run the main function
main().then(process.exit).catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});