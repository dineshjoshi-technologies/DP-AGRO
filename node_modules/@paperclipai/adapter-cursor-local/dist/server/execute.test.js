import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { describe, expect, it, vi } from "vitest";
import { runChildProcess } from "@paperclipai/adapter-utils/server-utils";
import { SANDBOX_INSTALL_COMMAND } from "../index.js";
import { execute } from "./execute.js";
const { setPrepareCursorSandboxCommand, } = vi.hoisted(() => {
    const setPrepareCursorSandboxCommand = vi.fn();
    return { setPrepareCursorSandboxCommand };
});
vi.mock("@paperclipai/adapter-utils/execution-target", async () => {
    const actual = await vi.importActual("@paperclipai/adapter-utils/execution-target");
    return {
        ...actual,
        startAdapterExecutionTargetPaperclipBridge: async () => null,
    };
});
vi.mock("./remote-command.js", async () => {
    const actual = await vi.importActual("./remote-command.js");
    return {
        ...actual,
        prepareCursorSandboxCommand: async (input) => {
            return setPrepareCursorSandboxCommand(input);
        },
    };
});
function buildFakeAgentScript(captureDir) {
    return `#!/bin/sh
cat > ${JSON.stringify(path.join(captureDir, "prompt.txt"))}
printf '%s' "$0" > ${JSON.stringify(path.join(captureDir, "command.txt"))}
printf '%s' "$PATH" > ${JSON.stringify(path.join(captureDir, "path.txt"))}
printf '%s\\n' '{"type":"system","subtype":"init","session_id":"cursor-session-fresh-1","model":"auto"}'
printf '%s\\n' '{"type":"assistant","message":{"content":[{"type":"output_text","text":"hello"}]}}'
printf '%s\\n' '{"type":"result","subtype":"success","session_id":"cursor-session-fresh-1","result":"ok"}'
`;
}
function buildInstallSimulationCommand(commandPath, captureDir) {
    return [
        `mkdir -p ${JSON.stringify(path.dirname(commandPath))}`,
        `mkdir -p ${JSON.stringify(captureDir)}`,
        `cat > ${JSON.stringify(commandPath)} <<'EOF'`,
        buildFakeAgentScript(captureDir),
        "EOF",
        `chmod +x ${JSON.stringify(commandPath)}`,
    ].join("\n");
}
function createFreshLeaseSandboxRunner(options) {
    let counter = 0;
    const installCommands = [];
    const systemPath = [
        "/usr/local/bin",
        "/opt/homebrew/bin",
        "/usr/local/sbin",
        "/usr/bin",
        "/bin",
        "/usr/sbin",
        "/sbin",
    ].join(path.delimiter);
    return {
        installCommands,
        execute: async (input) => {
            counter += 1;
            const args = [...(input.args ?? [])];
            if (args[1] === SANDBOX_INSTALL_COMMAND) {
                installCommands.push(args[1]);
                args[1] = buildInstallSimulationCommand(options.installCommandPath, options.captureDir);
            }
            const inheritedPath = input.env?.PATH ?? systemPath;
            const pathWithLocalBin = `${path.join(options.homeDir, ".local", "bin")}${path.delimiter}${inheritedPath}`;
            const env = {
                ...(input.env ?? {}),
                HOME: input.env?.HOME ?? options.homeDir,
                PATH: pathWithLocalBin,
            };
            return await runChildProcess(`cursor-fresh-lease-${counter}`, input.command, args, {
                cwd: input.cwd ?? process.cwd(),
                env,
                stdin: input.stdin,
                timeoutSec: Math.max(1, Math.ceil((input.timeoutMs ?? 30_000) / 1000)),
                graceSec: 5,
                onLog: input.onLog ?? (async () => { }),
                onSpawn: input.onSpawn
                    ? async (meta) => input.onSpawn?.({ pid: meta.pid, startedAt: meta.startedAt })
                    : undefined,
            });
        },
    };
}
describe("cursor execute", () => {
    it("installs the default agent command on a fresh sandbox lease before execution", async () => {
        setPrepareCursorSandboxCommand.mockReset();
        setPrepareCursorSandboxCommand.mockImplementation(async (input) => {
            const actual = await vi.importActual("./remote-command.js");
            return actual.prepareCursorSandboxCommand(input);
        });
        const root = await fs.mkdtemp(path.join(os.tmpdir(), "paperclip-cursor-fresh-lease-"));
        const homeDir = path.join(root, "home");
        const workspace = path.join(root, "workspace");
        const remoteWorkspace = path.join(root, "remote-workspace");
        const captureDir = path.join(root, "capture");
        const agentPath = path.join(homeDir, ".local", "bin", "agent");
        await fs.mkdir(workspace, { recursive: true });
        await fs.mkdir(remoteWorkspace, { recursive: true });
        const runner = createFreshLeaseSandboxRunner({
            homeDir,
            installCommandPath: agentPath,
            captureDir,
        });
        const previousHome = process.env.HOME;
        process.env.HOME = homeDir;
        try {
            const result = await execute({
                runId: "run-fresh-lease-1",
                agent: {
                    id: "agent-1",
                    companyId: "company-1",
                    name: "Cursor Coder",
                    adapterType: "cursor",
                    adapterConfig: {},
                },
                runtime: {
                    sessionId: null,
                    sessionParams: null,
                    sessionDisplayId: null,
                    taskKey: null,
                },
                executionTarget: {
                    kind: "remote",
                    transport: "sandbox",
                    remoteCwd: remoteWorkspace,
                    runner,
                    timeoutMs: 30_000,
                },
                config: {
                    command: "agent",
                    cwd: workspace,
                    promptTemplate: "Follow the paperclip heartbeat.",
                },
                context: {},
                authToken: "run-jwt-token",
                onLog: async () => { },
            });
            expect(result.exitCode).toBe(0);
            expect(result.errorMessage).toBeNull();
            expect(runner.installCommands).toEqual([SANDBOX_INSTALL_COMMAND]);
            const command = await fs.readFile(path.join(captureDir, "command.txt"), "utf8");
            const runtimePath = await fs.readFile(path.join(captureDir, "path.txt"), "utf8");
            const prompt = await fs.readFile(path.join(captureDir, "prompt.txt"), "utf8");
            expect(command).toBe(agentPath);
            expect(runtimePath.split(path.delimiter)).toContain(path.join(homeDir, ".local", "bin"));
            expect(prompt).toContain("Follow the paperclip heartbeat.");
        }
        finally {
            if (previousHome === undefined)
                delete process.env.HOME;
            else
                process.env.HOME = previousHome;
            await fs.rm(root, { recursive: true, force: true });
        }
    });
    it("reruns sandbox command resolution after managed runtime setup and keeps the original sandbox home", async () => {
        setPrepareCursorSandboxCommand.mockReset();
        const prepareInputs = [];
        let finalPreparedCommand = null;
        const rootDir = await fs.mkdtemp(path.join(os.tmpdir(), "paperclip-cursor-fresh-lease-managed-"));
        const workspaceDir = path.join(rootDir, "workspace");
        const remoteWorkspace = path.join(rootDir, "remote-workspace");
        const systemHomeDir = path.join(rootDir, "system-home");
        const managedCaptureDir = path.join(rootDir, "managed-capture");
        await fs.mkdir(managedCaptureDir, { recursive: true });
        await fs.mkdir(workspaceDir, { recursive: true });
        await fs.mkdir(remoteWorkspace, { recursive: true });
        const preferredAgentScript = `#!/bin/sh
printf '%s\\n' '{"type":"system","subtype":"init","session_id":"cursor-session-fresh-1","model":"auto"}'
printf '%s\\n' '{"type":"assistant","message":{"content":[{"type":"output_text","text":"hello"}]}}'
printf '%s\\n' '{"type":"result","subtype":"success","session_id":"cursor-session-fresh-1","result":"ok"}'
`;
        setPrepareCursorSandboxCommand.mockImplementation(async (input) => {
            const call = prepareInputs.length;
            prepareInputs.push(input);
            if (call === 0) {
                return {
                    command: input.command,
                    env: input.env,
                    remoteSystemHomeDir: systemHomeDir,
                    addedPathEntry: null,
                    preferredCommandPath: null,
                };
            }
            expect(input.remoteSystemHomeDirHint).toBe(systemHomeDir);
            const preferredCommandPath = path.join(systemHomeDir, ".local", "bin", input.command);
            finalPreparedCommand = preferredCommandPath;
            const runtimeEnv = {
                ...input.env,
                PATH: `${path.join(systemHomeDir, ".local", "bin")}${path.delimiter}${input.env.PATH}`,
            };
            await fs.mkdir(path.dirname(preferredCommandPath), { recursive: true });
            await fs.writeFile(preferredCommandPath, preferredAgentScript);
            await fs.chmod(preferredCommandPath, 0o755);
            await fs.writeFile(path.join(managedCaptureDir, "agent-output.log"), preferredCommandPath);
            return {
                command: preferredCommandPath,
                env: runtimeEnv,
                remoteSystemHomeDir: systemHomeDir,
                addedPathEntry: path.join(systemHomeDir, ".local", "bin"),
                preferredCommandPath,
            };
        });
        const runnerState = {
            commands: [],
        };
        const runner = {
            execute: async (input) => {
                runnerState.commands.push(input.command);
                if (input.command === "sh") {
                    return {
                        exitCode: 0,
                        signal: null,
                        timedOut: false,
                        stdout: "",
                        stderr: "",
                        pid: 555,
                        startedAt: new Date().toISOString(),
                    };
                }
                return runChildProcess(`cursor-fresh-lease-${runnerState.commands.length}`, input.command, input.args ?? [], {
                    cwd: remoteWorkspace,
                    env: input.env ?? {},
                    timeoutSec: 30,
                    graceSec: 5,
                    onLog: async () => { },
                    onSpawn: async () => { },
                });
            },
        };
        const runMeta = [];
        const previousHome = process.env.HOME;
        process.env.HOME = systemHomeDir;
        try {
            const command = "agent";
            const result = await execute({
                runId: "run-fresh-lease-managed",
                agent: {
                    id: "agent-1",
                    companyId: "company-1",
                    name: "Cursor Coder",
                    adapterType: "cursor",
                    adapterConfig: {},
                },
                runtime: {
                    sessionId: null,
                    sessionParams: null,
                    sessionDisplayId: null,
                    taskKey: null,
                },
                executionTarget: {
                    kind: "remote",
                    transport: "sandbox",
                    remoteCwd: remoteWorkspace,
                    providerKey: "fixture",
                    runner: runner,
                    timeoutMs: 30_000,
                },
                config: {
                    command,
                    cwd: workspaceDir,
                    promptTemplate: "Run against runtime-managed command.",
                },
                context: {},
                authToken: "run-jwt-token",
                onLog: async () => { },
                onMeta: async (meta) => {
                    runMeta.push(meta);
                },
            });
            expect(result.exitCode).toBe(0);
            expect(prepareInputs).toHaveLength(2);
            expect(finalPreparedCommand).not.toBeNull();
            expect(finalPreparedCommand).toMatch(/\.local\/(bin|sbin)\/agent$/);
            const resolvedCommand = runMeta.find(Boolean)?.command;
            expect(resolvedCommand).toMatch(/\.local\/bin\/agent$/);
            expect(resolvedCommand).toContain(path.join(systemHomeDir, ".local", "bin", command));
        }
        finally {
            if (previousHome === undefined)
                delete process.env.HOME;
            else
                process.env.HOME = previousHome;
            await fs.rm(rootDir, { recursive: true, force: true });
        }
    });
});
//# sourceMappingURL=execute.test.js.map