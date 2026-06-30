import type { AdapterExecutionContext, AdapterExecutionResult } from "@paperclipai/adapter-utils";
type SessionKeyStrategy = "issue" | "agent" | "run" | "none";
type SseFrame = {
    event: string | null;
    data: string;
};
type TerminalState = {
    runId: string;
    status: string;
    eventName?: string | null;
    payload?: Record<string, unknown> | null;
    output?: string | null;
};
type TextRedactor = (value: string) => string;
export declare function resolveSessionKey(input: {
    strategy: SessionKeyStrategy;
    companyId: string;
    agentId: string;
    runId: string;
    issueId: string | null;
}): string | null;
export declare function parseSseFramesForTest(buffer: string): {
    frames: SseFrame[];
    rest: string;
};
export declare function mapFinalResultForTest(input: {
    terminal: TerminalState;
    outputChunks: string[];
    sessionKey: string | null;
    strategy: SessionKeyStrategy;
    redactText?: TextRedactor;
}): AdapterExecutionResult;
export declare function execute(ctx: AdapterExecutionContext): Promise<AdapterExecutionResult>;
export {};
//# sourceMappingURL=execute.d.ts.map