import { createHash } from "node:crypto";
import { models as DIRECT_MODELS } from "../index.js";
const ANTHROPIC_MODELS_ENDPOINT = "/v1/models";
const ANTHROPIC_MODELS_TIMEOUT_MS = 5000;
const ANTHROPIC_MODELS_CACHE_TTL_MS = 60_000;
const ANTHROPIC_API_VERSION = "2023-06-01";
/** AWS Bedrock model IDs — region-qualified identifiers required by the Bedrock API. */
const BEDROCK_MODELS = [
    { id: "us.anthropic.claude-opus-4-8-v1", label: "Bedrock Opus 4.8" },
    { id: "us.anthropic.claude-fable-5-v1", label: "Bedrock Fable 5" },
    { id: "us.anthropic.claude-opus-4-6-v1", label: "Bedrock Opus 4.6" },
    { id: "us.anthropic.claude-sonnet-4-5-20250929-v2:0", label: "Bedrock Sonnet 4.5" },
    { id: "us.anthropic.claude-haiku-4-5-20251001-v1:0", label: "Bedrock Haiku 4.5" },
];
let cached = null;
function isBedrockEnv() {
    return (process.env.CLAUDE_CODE_USE_BEDROCK === "1" ||
        process.env.CLAUDE_CODE_USE_BEDROCK === "true" ||
        (typeof process.env.ANTHROPIC_BEDROCK_BASE_URL === "string" &&
            process.env.ANTHROPIC_BEDROCK_BASE_URL.trim().length > 0));
}
function fingerprint(apiKey) {
    const digest = createHash("sha256").update(apiKey).digest("base64url").slice(0, 16);
    return `${apiKey.length}:${digest}`;
}
function dedupeModels(models) {
    const seen = new Set();
    const deduped = [];
    for (const model of models) {
        const id = model.id.trim();
        if (!id || seen.has(id))
            continue;
        seen.add(id);
        deduped.push({ id, label: model.label.trim() || id });
    }
    return deduped;
}
function mergedWithFallback(models) {
    return dedupeModels([
        ...models,
        ...DIRECT_MODELS,
    ]);
}
function resolveAnthropicApiKey() {
    const apiKey = process.env.ANTHROPIC_API_KEY?.trim();
    return apiKey && apiKey.length > 0 ? apiKey : null;
}
function resolveAnthropicBaseUrl() {
    const baseUrl = process.env.ANTHROPIC_BASE_URL?.trim();
    return baseUrl && baseUrl.length > 0 ? baseUrl.replace(/\/+$/, "") : "https://api.anthropic.com";
}
async function fetchAnthropicModels(apiKey, baseUrl) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), ANTHROPIC_MODELS_TIMEOUT_MS);
    try {
        const response = await fetch(`${baseUrl}${ANTHROPIC_MODELS_ENDPOINT}`, {
            headers: {
                "anthropic-version": ANTHROPIC_API_VERSION,
                "x-api-key": apiKey,
            },
            signal: controller.signal,
        });
        if (!response.ok)
            return [];
        const payload = (await response.json());
        const data = Array.isArray(payload.data) ? payload.data : [];
        const models = [];
        for (const item of data) {
            if (typeof item !== "object" || item === null)
                continue;
            const record = item;
            if (typeof record.id !== "string" || record.id.trim().length === 0)
                continue;
            const displayName = typeof record.display_name === "string" && record.display_name.trim().length > 0
                ? record.display_name
                : record.id;
            models.push({
                id: record.id,
                label: displayName,
            });
        }
        return dedupeModels(models);
    }
    catch (error) {
        console.warn("[paperclip] Claude model discovery failed", {
            error: error instanceof Error ? error.message : String(error),
        });
        return [];
    }
    finally {
        clearTimeout(timeout);
    }
}
async function loadClaudeModels(options) {
    if (isBedrockEnv())
        return dedupeModels(BEDROCK_MODELS);
    const fallback = dedupeModels(DIRECT_MODELS);
    const apiKey = resolveAnthropicApiKey();
    if (!apiKey)
        return fallback;
    const now = Date.now();
    const baseUrl = resolveAnthropicBaseUrl();
    const keyFingerprint = fingerprint(apiKey);
    if (options?.forceRefresh !== true &&
        cached &&
        cached.keyFingerprint === keyFingerprint &&
        cached.baseUrl === baseUrl &&
        cached.expiresAt > now) {
        return cached.models;
    }
    const fetched = await fetchAnthropicModels(apiKey, baseUrl);
    if (fetched.length > 0) {
        const merged = mergedWithFallback(fetched);
        cached = {
            keyFingerprint,
            baseUrl,
            expiresAt: now + ANTHROPIC_MODELS_CACHE_TTL_MS,
            models: merged,
        };
        return merged;
    }
    if (cached && cached.keyFingerprint === keyFingerprint && cached.baseUrl === baseUrl && cached.models.length > 0) {
        return cached.models;
    }
    return fallback;
}
/**
 * Return the model list appropriate for the current auth mode.
 * When Bedrock env vars are detected, returns Bedrock-native model IDs;
 * otherwise returns standard Anthropic API model IDs.
 */
export async function listClaudeModels() {
    return loadClaudeModels();
}
export async function refreshClaudeModels() {
    return loadClaudeModels({ forceRefresh: true });
}
export function resetClaudeModelsCacheForTests() {
    cached = null;
}
/** Check whether a model ID is a Bedrock-native identifier (not an Anthropic API short name). */
/** Bedrock model IDs use region-qualified prefixes (e.g. us.anthropic.*, eu.anthropic.*) or ARNs. */
export function isBedrockModelId(model) {
    return /^\w+\.anthropic\./.test(model) || model.startsWith("arn:aws:bedrock:");
}
//# sourceMappingURL=models.js.map