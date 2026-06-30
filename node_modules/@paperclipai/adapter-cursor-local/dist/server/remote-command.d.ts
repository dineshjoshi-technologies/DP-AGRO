import { type AdapterExecutionTarget } from "@paperclipai/adapter-utils/execution-target";
export declare function isDefaultCursorCommand(command: string): boolean;
export type PreparedCursorSandboxCommand = {
    command: string;
    env: Record<string, string>;
    remoteSystemHomeDir: string | null;
    addedPathEntry: string | null;
    preferredCommandPath: string | null;
};
export declare function prepareCursorSandboxCommand(input: {
    runId: string;
    target: AdapterExecutionTarget | null | undefined;
    command: string;
    cwd: string;
    env: Record<string, string>;
    remoteSystemHomeDirHint?: string | null;
    timeoutSec: number;
    graceSec: number;
}): Promise<PreparedCursorSandboxCommand>;
//# sourceMappingURL=remote-command.d.ts.map