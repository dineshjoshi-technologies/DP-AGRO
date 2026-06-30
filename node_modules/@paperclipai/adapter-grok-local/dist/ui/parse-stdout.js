import { applyTurnBoundary, createTurnBoundaryState } from "../shared/turn-boundary.js";
function safeJsonParse(text) {
    try {
        return JSON.parse(text);
    }
    catch {
        return null;
    }
}
function asRecord(value) {
    if (typeof value !== "object" || value === null || Array.isArray(value))
        return null;
    return value;
}
function asString(value, fallback = "") {
    return typeof value === "string" ? value : fallback;
}
function extractErrorText(value) {
    if (typeof value === "string")
        return value;
    const record = asRecord(value);
    if (!record)
        return "";
    return asString(record.message) || asString(record.detail) || asString(record.code);
}
function parseLineInternal(line, ts, thoughtBoundary) {
    const parsed = asRecord(safeJsonParse(line));
    if (!parsed) {
        return [{ kind: "stdout", ts, text: line }];
    }
    const type = asString(parsed.type).trim();
    if (type === "thought") {
        const text = asString(parsed.data);
        if (!text)
            return [];
        return [{ kind: "thinking", ts, text: applyTurnBoundary(thoughtBoundary, text), delta: true }];
    }
    if (type === "text") {
        const text = asString(parsed.data);
        if (!text)
            return [];
        return [{ kind: "assistant", ts, text, delta: true }];
    }
    if (type === "error") {
        const text = asString(parsed.data) || asString(parsed.message) || extractErrorText(parsed.error);
        return text ? [{ kind: "stderr", ts, text }] : [{ kind: "stderr", ts, text: "Grok error" }];
    }
    if (type === "end") {
        const stopReason = asString(parsed.stopReason).trim();
        const sessionId = asString(parsed.sessionId).trim();
        const parts = [
            stopReason ? `stop_reason=${stopReason}` : "",
            sessionId ? `session=${sessionId}` : "",
        ].filter(Boolean);
        return [{ kind: "system", ts, text: parts.join(" ") || "run completed" }];
    }
    return [{ kind: "system", ts, text: `event: ${type || "unknown"}` }];
}
export function createGrokStdoutParser() {
    let thoughtBoundary = createTurnBoundaryState();
    return {
        parseLine(line, ts) {
            return parseLineInternal(line, ts, thoughtBoundary);
        },
        reset() {
            thoughtBoundary = createTurnBoundaryState();
        },
    };
}
// Stateless fallback for callers that haven't migrated to the stateful factory.
// Without state, consecutive thought chunks at reasoning-turn boundaries can
// still appear merged; prefer createGrokStdoutParser for live transcripts.
export function parseGrokStdoutLine(line, ts) {
    return parseLineInternal(line, ts, createTurnBoundaryState());
}
//# sourceMappingURL=parse-stdout.js.map