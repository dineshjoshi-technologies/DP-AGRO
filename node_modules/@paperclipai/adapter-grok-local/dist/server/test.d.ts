import type { AdapterEnvironmentTestContext, AdapterEnvironmentTestResult } from "@paperclipai/adapter-utils";
export interface GrokModelsProbe {
    authenticated: boolean;
    defaultModel: string | null;
    models: string[];
}
export declare function parseGrokModelsOutput(stdout: string): GrokModelsProbe;
export declare function testEnvironment(ctx: AdapterEnvironmentTestContext): Promise<AdapterEnvironmentTestResult>;
//# sourceMappingURL=test.d.ts.map