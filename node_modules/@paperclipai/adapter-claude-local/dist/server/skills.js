import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { buildRuntimeMountedSkillSnapshot, readPaperclipRuntimeSkillEntries, readInstalledSkillTargets, resolvePaperclipDesiredSkillNames, } from "@paperclipai/adapter-utils/server-utils";
const __moduleDir = path.dirname(fileURLToPath(import.meta.url));
function asString(value) {
    return typeof value === "string" && value.trim().length > 0 ? value.trim() : null;
}
function resolveClaudeSkillsHome(config) {
    const env = typeof config.env === "object" && config.env !== null && !Array.isArray(config.env)
        ? config.env
        : {};
    const configuredHome = asString(env.HOME);
    const home = configuredHome ? path.resolve(configuredHome) : os.homedir();
    return path.join(home, ".claude", "skills");
}
async function buildClaudeSkillSnapshot(config) {
    const availableEntries = await readPaperclipRuntimeSkillEntries(config, __moduleDir);
    const desiredSkills = resolvePaperclipDesiredSkillNames(config, availableEntries);
    const skillsHome = resolveClaudeSkillsHome(config);
    const installed = await readInstalledSkillTargets(skillsHome);
    return buildRuntimeMountedSkillSnapshot({
        adapterType: "claude_local",
        availableEntries,
        desiredSkills,
        configuredDetail: "Will be materialized into the stable Paperclip-managed Claude prompt bundle on the next run.",
        externalInstalled: installed,
        externalLocationLabel: "~/.claude/skills",
        externalDetail: "Installed outside Paperclip management in the Claude skills home.",
        skillsHome,
    });
}
export async function listClaudeSkills(ctx) {
    return buildClaudeSkillSnapshot(ctx.config);
}
export async function syncClaudeSkills(ctx, _desiredSkills) {
    return buildClaudeSkillSnapshot(ctx.config);
}
export function resolveClaudeDesiredSkillNames(config, availableEntries) {
    return resolvePaperclipDesiredSkillNames(config, availableEntries);
}
//# sourceMappingURL=skills.js.map