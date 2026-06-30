/**
 * Hermes Agent adapter for Paperclip.
 *
 * Runs Hermes Agent (https://github.com/NousResearch/hermes-agent)
 * as a managed employee in a Paperclip company. Hermes Agent is a
 * full-featured AI agent with 30+ native tools, persistent memory,
 * skills, session persistence, and MCP support.
 *
 * @packageDocumentation
 */
import type { ServerAdapterModule } from "@paperclipai/adapter-utils";
export declare const type = "hermes_local";
export declare const label = "Hermes Agent";
export { createServerAdapter as createHermesGatewayServerAdapter, agentConfigurationDoc as hermesGatewayAgentConfigurationDoc, label as hermesGatewayLabel, models as hermesGatewayModels, type as hermesGatewayType, } from "./gateway/index.js";
/**
 * Models available through Hermes Agent.
 *
 * Hermes supports any model via any provider. The Paperclip UI should
 * prefer detectModel() plus manual entry over curated placeholder models,
 * since Hermes availability depends on the user's local configuration.
 */
export declare const models: {
    id: string;
    label: string;
}[];
/**
 * Documentation shown in the Paperclip UI when configuring a Hermes agent.
 */
export declare const agentConfigurationDoc = "# Hermes Agent Configuration\n\nHermes Agent is a full-featured AI agent by Nous Research with 30+ native\ntools, persistent memory, session persistence, skills, and MCP support.\n\n## Prerequisites\n\n- Python 3.10+ installed\n- Hermes Agent installed: `pip install hermes-agent`\n- At least one LLM API key configured in ~/.hermes/.env\n\n## Core Configuration\n\n| Field | Type | Default | Description |\n|-------|------|---------|-------------|\n| model | string | (Hermes configured default) | Optional explicit model in provider/model format. Leave blank to use Hermes's configured default model. |\n| provider | string | (auto) | API provider: auto, openrouter, nous, openai-codex, zai, kimi-coding, minimax, minimax-cn. Usually not needed \u2014 Hermes auto-detects from model name. |\n| timeoutSec | number | 300 | Execution timeout in seconds |\n| graceSec | number | 10 | Grace period after SIGTERM before SIGKILL |\n\n## Tool Configuration\n\n| Field | Type | Default | Description |\n|-------|------|---------|-------------|\n| toolsets | string | (all) | Comma-separated toolsets to enable (e.g. \"terminal,file,web\") |\n\n## Session & Workspace\n\n| Field | Type | Default | Description |\n|-------|------|---------|-------------|\n| persistSession | boolean | true | Resume sessions across heartbeats |\n| worktreeMode | boolean | false | Use git worktree for isolated changes |\n| checkpoints | boolean | false | Enable filesystem checkpoints |\n\n## Advanced\n\n| Field | Type | Default | Description |\n|-------|------|---------|-------------|\n| hermesCommand | string | hermes | Path to hermes CLI binary |\n| verbose | boolean | false | Enable verbose output |\n| extraArgs | string[] | [] | Additional CLI arguments |\n| env | object | {} | Extra environment variables |\n| promptTemplate | string | (default) | Custom prompt template with {{variable}} placeholders |\n\n## Hermes-Originated Paperclip Tasks\n\nThis adapter package also ships a Hermes-facing Paperclip task bridge skill:\n`paperclip-task-bridge`. Use it when a user starts in Hermes and asks Hermes\nto create, comment on, update, or list Paperclip tasks.\n\nConfigure credentials through Hermes env/profile secrets, never in prompt text:\n\n- `PAPERCLIP_API_URL` - Paperclip base URL, with or without `/api`\n- `PAPERCLIP_BRIDGE_API_KEY` - Paperclip agent API key created with `scope.kind = \"task_bridge\"`\n- optional fallback `PAPERCLIP_API_KEY` - must still be a task_bridge key, never a normal claimed agent key\n- optional `PAPERCLIP_COMPANY_ID`, `PAPERCLIP_AGENT_ID`, and `PAPERCLIP_RUN_ID`\n\nThe bridge is separate from adapter execution:\n\n- `hermes_local` means Paperclip shells out to local `hermes chat`.\n- `hermes_gateway` means Paperclip wakes remote Hermes through Hermes's API server.\n- `paperclip-task-bridge` means Hermes calls Paperclip's REST API to manage tasks.\n\nCreate task bridge keys with a parent issue or project boundary. Do not expose\nnormal claimed Paperclip agent API keys to internet-facing Hermes chat/webhook\ntask-bridge surfaces.\n\n## Available Template Variables\n\n- `{{agentId}}` \u2014 Paperclip agent ID\n- `{{agentName}}` \u2014 Agent display name\n- `{{companyId}}` \u2014 Paperclip company ID\n- `{{companyName}}` \u2014 Company display name\n- `{{runId}}` \u2014 Current heartbeat run ID\n- `{{taskId}}` \u2014 Current task/issue ID (if assigned)\n- `{{taskTitle}}` \u2014 Task title (if assigned)\n- `{{taskBody}}` \u2014 Task description (if assigned)\n- `{{projectName}}` \u2014 Project name (if scoped to a project)\n";
/**
 * External adapter plugin entrypoint expected by Paperclip's adapter manager.
 */
export declare function createServerAdapter(): ServerAdapterModule;
export { createServerAdapter as createHermesLocalServerAdapter };
//# sourceMappingURL=index.d.ts.map