import type { AdapterExecutionTarget } from "@paperclipai/adapter-utils/execution-target";
export declare function claudeCommandLooksLike(command: string, expected?: string): boolean;
export declare function claudeCommandSupportsEffortFlag(input: {
    runId: string;
    command: string;
    target: AdapterExecutionTarget | null | undefined;
    cwd: string;
    env: Record<string, string>;
    timeoutSec: number;
    graceSec: number;
}): Promise<boolean | null>;
export declare function resetClaudeCliCapabilitiesCacheForTests(): void;
//# sourceMappingURL=cli-capabilities.d.ts.map