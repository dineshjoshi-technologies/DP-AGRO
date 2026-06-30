import type { TranscriptEntry } from "@paperclipai/adapter-utils";
export declare function createGrokStdoutParser(): {
    parseLine(line: string, ts: string): TranscriptEntry[];
    reset(): void;
};
export declare function parseGrokStdoutLine(line: string, ts: string): TranscriptEntry[];
//# sourceMappingURL=parse-stdout.d.ts.map