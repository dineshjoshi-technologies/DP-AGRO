import path from "node:path";
import { fileURLToPath } from "node:url";
import { buildRuntimeMountedSkillSnapshot, readPaperclipRuntimeSkillEntries, resolvePaperclipDesiredSkillNames, } from "@paperclipai/adapter-utils/server-utils";
const __moduleDir = path.dirname(fileURLToPath(import.meta.url));
async function buildCodexSkillSnapshot(config) {
    const availableEntries = await readPaperclipRuntimeSkillEntries(config, __moduleDir);
    const desiredSkills = resolvePaperclipDesiredSkillNames(config, availableEntries);
    return buildRuntimeMountedSkillSnapshot({
        adapterType: "codex_local",
        availableEntries,
        desiredSkills,
        configuredDetail: "Will be linked into the effective CODEX_HOME/skills/ directory on the next run.",
    });
}
export async function listCodexSkills(ctx) {
    return buildCodexSkillSnapshot(ctx.config);
}
export async function syncCodexSkills(ctx, _desiredSkills) {
    return buildCodexSkillSnapshot(ctx.config);
}
export function resolveCodexDesiredSkillNames(config, availableEntries) {
    return resolvePaperclipDesiredSkillNames(config, availableEntries);
}
//# sourceMappingURL=skills.js.map