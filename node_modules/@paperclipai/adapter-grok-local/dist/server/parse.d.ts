export interface ParsedGrokJsonl {
    sessionId: string | null;
    summary: string;
    thought: string;
    errorMessage: string | null;
    stopReason: string | null;
    requestId: string | null;
}
export declare function parseGrokJsonl(stdout: string): ParsedGrokJsonl;
export declare function isGrokUnknownSessionError(stdout: string, stderr: string): boolean;
//# sourceMappingURL=parse.d.ts.map