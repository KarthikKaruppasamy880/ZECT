import { useState, useEffect, useRef, useCallback } from "react";
import {
  Terminal,
  Play,
  Square,
  Trash2,
  FolderOpen,
  Settings,
  MonitorPlay,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Info,
  Loader2,
  Plus,
  ExternalLink,
} from "lucide-react";
import {
  runnerExecute,
  runnerStart,
  runnerStop,
  runnerProcesses,
  runnerOutput,
  runnerRemoveProcess,
  runnerConfigure,
} from "@/lib/api";

interface ProcessEntry {
  id: string;
  pid: number;
  label: string;
  cmd: string;
  cwd: string;
  running: boolean;
  exit_code: number | null;
  started_at: number;
  uptime_seconds: number;
  output_lines: number;
}

interface OutputData {
  lines: string[];
  total_lines: number;
  running: boolean;
  exit_code: number | null;
}

export default function AppRunner() {
  // --- State ---
  const [showGuide, setShowGuide] = useState(false);
  const [activeTab, setActiveTab] = useState<"terminal" | "configure" | "processes">("terminal");

  // Terminal state
  const [command, setCommand] = useState("");
  const [cwd, setCwd] = useState("");
  const [terminalOutput, setTerminalOutput] = useState<string[]>([]);
  const [executing, setExecuting] = useState(false);
  const terminalRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [commandHistory, setCommandHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  // Processes state
  const [processes, setProcesses] = useState<ProcessEntry[]>([]);
  const [selectedProcess, setSelectedProcess] = useState<string | null>(null);
  const [processOutput, setProcessOutput] = useState<OutputData | null>(null);
  const [polling, setPolling] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Configure state
  const [repoPath, setRepoPath] = useState("");
  const [installCmd, setInstallCmd] = useState("npm install");
  const [startupCmd, setStartupCmd] = useState("npm run dev");
  const [previewPort, setPreviewPort] = useState("5173");
  const [envVars, setEnvVars] = useState("");
  const [configuring, setConfiguring] = useState(false);
  const [configResult, setConfigResult] = useState<any>(null);

  // --- Effects ---

  // Scroll terminal to bottom
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [terminalOutput]);

  // Load processes on mount and periodically
  const loadProcesses = useCallback(async () => {
    try {
      const procs = await runnerProcesses();
      setProcesses(procs);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    loadProcesses();
    const interval = setInterval(loadProcesses, 5000);
    return () => clearInterval(interval);
  }, [loadProcesses]);

  // Poll selected process output
  useEffect(() => {
    if (selectedProcess && polling) {
      const poll = async () => {
        try {
          const data = await runnerOutput(selectedProcess, 0, 500);
          setProcessOutput(data);
          if (!data.running) {
            setPolling(false);
          }
        } catch {
          setPolling(false);
        }
      };
      poll();
      pollRef.current = setInterval(poll, 2000);
      return () => {
        if (pollRef.current) clearInterval(pollRef.current);
      };
    }
  }, [selectedProcess, polling]);

  // --- Handlers ---

  const executeCommand = async () => {
    if (!command.trim()) return;
    setExecuting(true);
    const displayCmd = `$ ${command}`;
    setTerminalOutput((prev) => [...prev, "", displayCmd]);
    setCommandHistory((prev) => [...prev, command]);
    setHistoryIndex(-1);

    try {
      const result = await runnerExecute(command, cwd || undefined, 30);
      const lines: string[] = [];
      if (result.stdout) lines.push(...result.stdout.split("\n"));
      if (result.stderr) lines.push(...result.stderr.split("\n").map((l: string) => `[stderr] ${l}`));
      if (result.exit_code !== 0) {
        lines.push(`[exit code: ${result.exit_code}]`);
      }
      setTerminalOutput((prev) => [...prev, ...lines]);
    } catch (err: any) {
      setTerminalOutput((prev) => [...prev, `[error] ${err.message}`]);
    }
    setCommand("");
    setExecuting(false);
    inputRef.current?.focus();
  };

  const startProcess = async () => {
    if (!command.trim()) return;
    setExecuting(true);
    setTerminalOutput((prev) => [...prev, "", `[starting] ${command}`]);

    try {
      const result = await runnerStart(command, cwd || undefined, undefined);
      setTerminalOutput((prev) => [...prev, `[started] PID ${result.pid} — ID: ${result.id}`]);
      setSelectedProcess(result.id);
      setPolling(true);
      loadProcesses();
    } catch (err: any) {
      setTerminalOutput((prev) => [...prev, `[error] ${err.message}`]);
    }
    setCommand("");
    setExecuting(false);
  };

  const stopProcess = async (id: string) => {
    try {
      await runnerStop(id);
      setTerminalOutput((prev) => [...prev, `[stopped] Process ${id}`]);
      loadProcesses();
    } catch (err: any) {
      setTerminalOutput((prev) => [...prev, `[error] ${err.message}`]);
    }
  };

  const removeProcess = async (id: string) => {
    try {
      await runnerRemoveProcess(id);
      if (selectedProcess === id) {
        setSelectedProcess(null);
        setProcessOutput(null);
      }
      loadProcesses();
    } catch (err: any) {
      setTerminalOutput((prev) => [...prev, `[error] ${err.message}`]);
    }
  };

  const handleConfigure = async () => {
    if (!repoPath.trim()) return;
    setConfiguring(true);
    setConfigResult(null);

    const envObj: Record<string, string> = {};
    if (envVars.trim()) {
      envVars.split("\n").forEach((line) => {
        const eqIdx = line.indexOf("=");
        if (eqIdx > 0) {
          envObj[line.slice(0, eqIdx).trim()] = line.slice(eqIdx + 1).trim();
        }
      });
    }

    try {
      const result = await runnerConfigure(repoPath, {
        install_command: installCmd || undefined,
        startup_command: startupCmd || undefined,
        preview_port: previewPort ? parseInt(previewPort) : undefined,
        env_vars: Object.keys(envObj).length > 0 ? envObj : undefined,
      });
      setConfigResult(result);
      if (result.process_id) {
        setSelectedProcess(result.process_id);
        setPolling(true);
      }
      loadProcesses();
    } catch (err: any) {
      setConfigResult({ error: err.message });
    }
    setConfiguring(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      executeCommand();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (commandHistory.length > 0) {
        const newIdx = historyIndex < commandHistory.length - 1 ? historyIndex + 1 : historyIndex;
        setHistoryIndex(newIdx);
        setCommand(commandHistory[commandHistory.length - 1 - newIdx]);
      }
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (historyIndex > 0) {
        const newIdx = historyIndex - 1;
        setHistoryIndex(newIdx);
        setCommand(commandHistory[commandHistory.length - 1 - newIdx]);
      } else {
        setHistoryIndex(-1);
        setCommand("");
      }
    }
  };

  const runningCount = processes.filter((p) => p.running).length;

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <MonitorPlay className="h-6 w-6 text-emerald-600" />
            App Runner
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Configure, run, and test your applications directly inside ZECT
          </p>
        </div>
        <div className="flex items-center gap-3">
          {runningCount > 0 && (
            <span className="px-2.5 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full">
              {runningCount} running
            </span>
          )}
          <button
            onClick={() => setShowGuide(!showGuide)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-slate-100 text-slate-600 hover:bg-slate-200 transition-colors"
          >
            <Info className="h-4 w-4" />
            Guide
          </button>
        </div>
      </div>

      {/* Guide */}
      {showGuide && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-5 space-y-3">
          <h3 className="font-semibold text-emerald-900">How to use App Runner</h3>
          <div className="text-sm text-emerald-800 space-y-2">
            <p>
              <strong>Terminal Tab</strong> — Run one-shot commands (like <code className="bg-emerald-100 px-1 rounded">ls</code>, <code className="bg-emerald-100 px-1 rounded">npm test</code>, <code className="bg-emerald-100 px-1 rounded">git status</code>). Use the &quot;Start Process&quot; button to run long-lived servers (like <code className="bg-emerald-100 px-1 rounded">npm run dev</code>).
            </p>
            <p>
              <strong>Configure Tab</strong> — Point to a repo on disk, set install and startup commands, define environment variables, and launch with one click. ZECT will install dependencies, start the dev server, and show the preview.
            </p>
            <p>
              <strong>Processes Tab</strong> — View all running and stopped processes. Click a process to see its live output. Stop or remove processes as needed.
            </p>
            <p>
              <strong>Preview</strong> — When a dev server is running, the preview panel shows the live app in an iframe. Set the correct port in Configure tab.
            </p>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-100 rounded-lg p-1">
        {(["terminal", "configure", "processes"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              activeTab === tab
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            {tab === "terminal" && <Terminal className="h-4 w-4 inline mr-1.5" />}
            {tab === "configure" && <Settings className="h-4 w-4 inline mr-1.5" />}
            {tab === "processes" && <MonitorPlay className="h-4 w-4 inline mr-1.5" />}
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
            {tab === "processes" && processes.length > 0 && (
              <span className="ml-1.5 px-1.5 py-0.5 bg-slate-200 text-slate-600 text-xs rounded-full">
                {processes.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Panel — Main Content */}
        <div className="space-y-4">
          {activeTab === "terminal" && (
            <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
              <div className="bg-slate-900 px-4 py-2 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="flex gap-1.5">
                    <div className="w-3 h-3 rounded-full bg-red-500" />
                    <div className="w-3 h-3 rounded-full bg-yellow-500" />
                    <div className="w-3 h-3 rounded-full bg-green-500" />
                  </div>
                  <span className="text-slate-400 text-xs ml-2">ZECT Terminal</span>
                </div>
                <button
                  onClick={() => setTerminalOutput([])}
                  className="text-slate-500 hover:text-slate-300 text-xs"
                >
                  Clear
                </button>
              </div>

              {/* Terminal Output */}
              <div
                ref={terminalRef}
                className="bg-slate-950 text-green-400 font-mono text-sm p-4 h-[400px] overflow-y-auto"
                onClick={() => inputRef.current?.focus()}
              >
                {terminalOutput.length === 0 && (
                  <div className="text-slate-600">
                    Welcome to ZECT App Runner. Type a command below.
                    <br />
                    Use &quot;Run&quot; for one-shot commands, &quot;Start Process&quot; for long-running servers.
                  </div>
                )}
                {terminalOutput.map((line, i) => (
                  <div
                    key={i}
                    className={
                      line.startsWith("$")
                        ? "text-cyan-400 font-semibold"
                        : line.startsWith("[stderr]") || line.startsWith("[error]")
                        ? "text-red-400"
                        : line.startsWith("[started]") || line.startsWith("[stopped]") || line.startsWith("[starting]")
                        ? "text-yellow-400"
                        : "text-green-300"
                    }
                  >
                    {line || "\u00A0"}
                  </div>
                ))}
                {executing && (
                  <div className="text-slate-500 flex items-center gap-2">
                    <Loader2 className="h-3 w-3 animate-spin" /> Running...
                  </div>
                )}
              </div>

              {/* Input */}
              <div className="bg-slate-900 border-t border-slate-800 p-3">
                <div className="flex items-center gap-2 mb-2">
                  <FolderOpen className="h-4 w-4 text-slate-500" />
                  <input
                    type="text"
                    placeholder="Working directory (leave empty for home)"
                    value={cwd}
                    onChange={(e) => setCwd(e.target.value)}
                    className="flex-1 bg-slate-800 text-slate-300 text-xs px-3 py-1.5 rounded-md border border-slate-700 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-emerald-400 font-mono text-sm">$</span>
                  <input
                    ref={inputRef}
                    type="text"
                    placeholder="Enter command..."
                    value={command}
                    onChange={(e) => setCommand(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={executing}
                    className="flex-1 bg-slate-800 text-green-300 font-mono text-sm px-3 py-2 rounded-md border border-slate-700 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none placeholder-slate-600"
                  />
                  <button
                    onClick={executeCommand}
                    disabled={executing || !command.trim()}
                    className="px-3 py-2 bg-emerald-600 text-white text-sm rounded-md hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
                  >
                    <Play className="h-3.5 w-3.5" />
                    Run
                  </button>
                  <button
                    onClick={startProcess}
                    disabled={executing || !command.trim()}
                    className="px-3 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
                    title="Start as background process (for dev servers, watchers, etc.)"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    Start Process
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab === "configure" && (
            <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-6 space-y-5">
              <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                <Settings className="h-5 w-5 text-blue-600" />
                Project Configuration
              </h3>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Repo Path</label>
                  <input
                    type="text"
                    placeholder="/path/to/your/project"
                    value={repoPath}
                    onChange={(e) => setRepoPath(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
                  />
                  <p className="text-xs text-slate-400 mt-1">Absolute path to the cloned repo on the server</p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Install Command</label>
                    <input
                      type="text"
                      placeholder="npm install"
                      value={installCmd}
                      onChange={(e) => setInstallCmd(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Startup Command</label>
                    <input
                      type="text"
                      placeholder="npm run dev"
                      value={startupCmd}
                      onChange={(e) => setStartupCmd(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Preview Port</label>
                  <input
                    type="text"
                    placeholder="5173"
                    value={previewPort}
                    onChange={(e) => setPreviewPort(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Environment Variables</label>
                  <textarea
                    placeholder={"NODE_ENV=development\nPORT=5173\nDATABASE_URL=postgresql://..."}
                    value={envVars}
                    onChange={(e) => setEnvVars(e.target.value)}
                    rows={4}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm font-mono focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
                  />
                  <p className="text-xs text-slate-400 mt-1">One per line: KEY=VALUE</p>
                </div>

                <button
                  onClick={handleConfigure}
                  disabled={configuring || !repoPath.trim()}
                  className="w-full px-4 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {configuring ? (
                    <><Loader2 className="h-4 w-4 animate-spin" /> Configuring...</>
                  ) : (
                    <><Rocket className="h-4 w-4" /> Install &amp; Launch</>
                  )}
                </button>

                {configResult && (
                  <div className={`p-4 rounded-lg text-sm ${configResult.error ? "bg-red-50 border border-red-200 text-red-700" : "bg-green-50 border border-green-200 text-green-700"}`}>
                    {configResult.error ? (
                      <p>Error: {configResult.error}</p>
                    ) : (
                      <div>
                        <p className="font-medium">Configuration complete!</p>
                        {configResult.steps?.map((step: any, i: number) => (
                          <div key={i} className="mt-2">
                            <p className="font-medium">{step.step}: {step.command}</p>
                            {step.exit_code !== undefined && (
                              <p className={step.exit_code === 0 ? "text-green-600" : "text-red-600"}>
                                Exit code: {step.exit_code}
                              </p>
                            )}
                            {step.process_id && <p>Process ID: {step.process_id}</p>}
                          </div>
                        ))}
                        {configResult.preview_url && (
                          <p className="mt-2">
                            Preview: <a href={configResult.preview_url} target="_blank" rel="noopener noreferrer" className="underline">{configResult.preview_url}</a>
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === "processes" && (
            <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
                <h3 className="font-semibold text-slate-900">Running Processes</h3>
                <button
                  onClick={loadProcesses}
                  className="text-slate-400 hover:text-slate-600"
                >
                  <RefreshCw className="h-4 w-4" />
                </button>
              </div>

              {processes.length === 0 ? (
                <div className="p-8 text-center text-slate-400">
                  <MonitorPlay className="h-10 w-10 mx-auto mb-3 opacity-40" />
                  <p className="text-sm">No processes running</p>
                  <p className="text-xs mt-1">Start a process from the Terminal or Configure tab</p>
                </div>
              ) : (
                <div className="divide-y divide-slate-100">
                  {processes.map((proc) => (
                    <div
                      key={proc.id}
                      className={`px-4 py-3 cursor-pointer hover:bg-slate-50 transition-colors ${
                        selectedProcess === proc.id ? "bg-blue-50 border-l-2 border-blue-500" : ""
                      }`}
                      onClick={() => {
                        setSelectedProcess(proc.id);
                        setPolling(proc.running);
                        runnerOutput(proc.id, 0, 500).then(setProcessOutput).catch(() => {});
                      }}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className={`w-2 h-2 rounded-full ${proc.running ? "bg-green-500 animate-pulse" : "bg-slate-400"}`} />
                          <span className="font-medium text-sm text-slate-900">{proc.label}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          {proc.running && (
                            <span className="text-xs text-slate-500">
                              {Math.round(proc.uptime_seconds)}s
                            </span>
                          )}
                          {proc.running ? (
                            <button
                              onClick={(e) => { e.stopPropagation(); stopProcess(proc.id); }}
                              className="p-1 text-red-500 hover:bg-red-50 rounded"
                              title="Stop"
                            >
                              <Square className="h-3.5 w-3.5" />
                            </button>
                          ) : (
                            <button
                              onClick={(e) => { e.stopPropagation(); removeProcess(proc.id); }}
                              className="p-1 text-slate-400 hover:bg-slate-100 rounded"
                              title="Remove"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          )}
                        </div>
                      </div>
                      <p className="text-xs text-slate-500 mt-1 font-mono truncate">{proc.cmd}</p>
                      <p className="text-xs text-slate-400 mt-0.5">{proc.cwd}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Panel — Process Output / Preview */}
        <div className="space-y-4">
          {/* Process Output */}
          {selectedProcess && processOutput && (
            <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
              <div className="bg-slate-800 px-4 py-2 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${processOutput.running ? "bg-green-500 animate-pulse" : "bg-slate-500"}`} />
                  <span className="text-slate-300 text-xs font-mono">Process Output — {selectedProcess}</span>
                </div>
                <div className="flex items-center gap-2">
                  {processOutput.running && (
                    <button
                      onClick={() => {
                        runnerOutput(selectedProcess, 0, 500).then(setProcessOutput).catch(() => {});
                      }}
                      className="text-slate-500 hover:text-slate-300"
                    >
                      <RefreshCw className="h-3.5 w-3.5" />
                    </button>
                  )}
                  <span className="text-slate-500 text-xs">{processOutput.total_lines} lines</span>
                </div>
              </div>
              <div className="bg-slate-950 text-green-300 font-mono text-xs p-4 h-[250px] overflow-y-auto">
                {processOutput.lines.length === 0 ? (
                  <span className="text-slate-600">Waiting for output...</span>
                ) : (
                  processOutput.lines.map((line, i) => (
                    <div key={i} className={line.startsWith("[stderr]") ? "text-red-400" : ""}>
                      {line || "\u00A0"}
                    </div>
                  ))
                )}
                {!processOutput.running && processOutput.exit_code !== null && (
                  <div className={`mt-2 font-semibold ${processOutput.exit_code === 0 ? "text-green-400" : "text-red-400"}`}>
                    Process exited with code {processOutput.exit_code}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Preview Panel */}
          <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
              <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                <ExternalLink className="h-4 w-4 text-emerald-600" />
                Live Preview
              </h3>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  placeholder="http://localhost:5173"
                  value={previewPort ? `http://localhost:${previewPort}` : ""}
                  readOnly
                  className="text-xs bg-slate-50 border border-slate-200 rounded px-2 py-1 w-48"
                />
                {previewPort && (
                  <a
                    href={`http://localhost:${previewPort}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:text-blue-700"
                  >
                    <ExternalLink className="h-4 w-4" />
                  </a>
                )}
              </div>
            </div>
            <div className="bg-slate-50 h-[350px] flex items-center justify-center">
              {runningCount > 0 && previewPort ? (
                <iframe
                  src={`http://localhost:${previewPort}`}
                  className="w-full h-full border-0"
                  title="App Preview"
                  sandbox="allow-same-origin allow-scripts allow-popups allow-forms"
                />
              ) : (
                <div className="text-center text-slate-400">
                  <MonitorPlay className="h-12 w-12 mx-auto mb-3 opacity-30" />
                  <p className="text-sm">No app running</p>
                  <p className="text-xs mt-1">Start a dev server to see live preview here</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
