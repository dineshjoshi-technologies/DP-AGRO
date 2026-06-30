import type { AdapterExecutionContext, AdapterExecutionResult } from "@paperclipai/adapter-utils";
type SessionKeyStrategy = "fixed" | "issue" | "run";
export declare function resolveSessionKey(input: {
    strategy: SessionKeyStrategy;
    configuredSessionKey: string | null;
    agentId: string | null;
    runId: string;
    issueId: string | null;
}): string;
export declare function buildAgentParams(input: {
    payloadTemplate: Record<string, unknown>;
    message: string;
    sessionKey: string;
    runId: string;
    configuredAgentId: string | null;
    waitTimeoutMs: number;
}): Record<string, unknown>;
export declare function execute(ctx: AdapterExecutionContext): Promise<AdapterExecutionResult>;
export {};
//# sourceMappingURL=execute.d.ts.map