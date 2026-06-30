export declare const INSECURE_REMOTE_HTTP_ESCAPE_HATCH = "dangerouslyAllowInsecureRemoteHttp";
export declare function parseBooleanLike(value: unknown): boolean | null;
export declare function isLoopbackHostname(hostname: string): boolean;
export declare function isRemotePlainHttp(url: URL): boolean;
export declare function allowsInsecureRemoteHttp(config: Record<string, unknown>): boolean;
export declare function remotePlainHttpDeniedMessage(hostname: string): string;
//# sourceMappingURL=transport-security.d.ts.map