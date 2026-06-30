type PreparedPiRuntimeConfig = {
    env: Record<string, string>;
    notes: string[];
    /** The managed agent-config dir, or null when no provider config was written. */
    agentConfigDir: string | null;
    cleanup: () => Promise<void>;
};
export declare function preparePiRuntimeConfig(input: {
    env: Record<string, string>;
}): Promise<PreparedPiRuntimeConfig>;
export {};
//# sourceMappingURL=runtime-config.d.ts.map