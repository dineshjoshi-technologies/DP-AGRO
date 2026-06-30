import path from "node:path";
import { fileURLToPath } from "node:url";
import { buildRuntimeMountedSkillSnapshot, readPaperclipRuntimeSkillEntries, resolvePaperclipDesiredSkillNames, } from "@paperclipai/adapter-utils/server-utils";
const __moduleDir = path.dirname(fileURLToPath(import.meta.url));
async function buildGrokSkillSnapshot(config) {
    const availableEntries = await readPaperclipRuntimeSkillEntries(config, __moduleDir);
    const desiredSkills = resolvePaperclipDesiredSkillNames(config, availableEntries);
    return buildRuntimeMountedSkillSnapshot({
        adapterType: "grok_local",
        availableEntries,
        desiredSkills,
        configuredDetail: "Will be copied into `.claude/skills` in the execution workspace on the next run.",
    });
}
export async function listGrokSkills(ctx) {
    return buildGrokSkillSnapshot(ctx.config);
}
export async function syncGrokSkills(ctx, _desiredSkills) {
    return buildGrokSkillSnapshot(ctx.config);
}
//# sourceMappingURL=skills.js.map