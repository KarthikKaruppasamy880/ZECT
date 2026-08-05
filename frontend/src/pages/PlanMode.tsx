import { useState, useRef, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { generatePlan, saveContext, loadContext, clearContext } from "@/lib/api";
import { useWorkspaceRepoContext } from "@/hooks/useWorkspaceRepoContext";
import { contextPageFor } from "@/lib/workspaceContext";
import CodeOutput from "@/components/CodeOutput";
import ModelSelector from "@/components/ModelSelector";
import PromptHygieneTips from "@/components/PromptHygieneTips";
import ConversationHistory from "@/components/ConversationHistory";
import {
  ClipboardList,
  Loader2,
  AlertCircle,
  Copy,
  Check,
  Zap,
  Plus,
  X,
  FileText,
  FolderGit2,
  FileCode,
  Upload,
  ArrowRight,
  Hammer,
} from "lucide-react";

interface AttachedFile {
  id: string;
  name: string;
  type: "file" | "repo" | "snippet";
  content: string;
}

export default function PlanMode() {
  const navigate = useNavigate();
  const location = useLocation();
  const {
    activeRepoId,
    projectKey,
    localPath,
    blueprintPrompt,
    loadSavedBlueprint,
    clearBlueprintContext,
    loadBlueprintPrompt,
  } = useWorkspaceRepoContext();
  const [description, setDescription] = useState("");
  const [repoContext, setRepoContext] = useState("");
  const [constraints, setConstraints] = useState("");
  const [selectedModel, setSelectedModel] = useState("gpt-4o-mini");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [plan, setPlan] = useState<string | null>(null);
  const [phases, setPhases] = useState<string[]>([]);
  const [tokensUsed, setTokensUsed] = useState(0);
  const [modelUsed, setModelUsed] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([]);
  const [showAddPanel, setShowAddPanel] = useState(false);
  const [newFileName, setNewFileName] = useState("");
  const [newFileContent, setNewFileContent] = useState("");
  const [newFileType, setNewFileType] = useState<"file" | "repo" | "snippet">("file");
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    void (async () => {
      const state = location.state as { projectDescription?: string; repoContext?: string } | null;
      if (state?.projectDescription) setDescription(state.projectDescription);
      if (state?.repoContext) {
        setRepoContext(state.repoContext);
        setShowAdvanced(true);
        return;
      }
      if (!projectKey) return;
      const session = await loadContext(contextPageFor("plan", projectKey), ["project_description", "repo_context"]).catch(() => null);
      const savedDesc = session?.entries.find((e) => e.key === "project_description")?.value;
      const savedCtx = session?.entries.find((e) => e.key === "repo_context")?.value;
      if (savedDesc && !state?.projectDescription) setDescription(savedDesc);
      if (savedCtx) {
        setRepoContext(savedCtx);
        setShowAdvanced(true);
        return;
      }
      const ws = await loadContext(contextPageFor("workspace", projectKey), ["blueprint_prompt", "last_ask_summary"]).catch(() => null);
      const bp =
        ws?.entries.find((e) => e.key === "blueprint_prompt")?.value ||
        blueprintPrompt ||
        (await loadSavedBlueprint());
      const askSummary = ws?.entries.find((e) => e.key === "last_ask_summary")?.value;
      if (bp && !savedCtx) {
        setRepoContext(bp);
        setShowAdvanced(true);
      }
      if (askSummary && !state?.projectDescription && !savedDesc) {
        setDescription(`Continue from Ask triage:\n\n${askSummary.slice(0, 4000)}`);
      }
    })();
  }, [location.state, blueprintPrompt, loadSavedBlueprint, projectKey]);

  const handleAddFile = () => {
    if (!newFileName.trim() || !newFileContent.trim()) return;
    setAttachedFiles((prev) => [
      ...prev,
      { id: Date.now().toString(), name: newFileName.trim(), type: newFileType, content: newFileContent.trim() },
    ]);
    setNewFileName("");
    setNewFileContent("");
    setShowAddPanel(false);
  };

  const handleBrowseFiles = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    Array.from(files).forEach((file) => {
      const reader = new FileReader();
      reader.onload = (ev) => {
        const content = ev.target?.result as string;
        setAttachedFiles((prev) => [
          ...prev,
          { id: `${Date.now()}-${file.name}`, name: file.name, type: "file", content },
        ]);
      };
      reader.readAsText(file);
    });
    e.target.value = "";
  };

  const handleRemoveFile = (id: string) => {
    setAttachedFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const handleGenerate = async () => {
    if (!description.trim()) {
      setError("Please describe the project or feature you want to plan.");
      return;
    }
    setLoading(true);
    setError(null);
    setPlan(null);
    try {
      // Build context from attached files
      let context = repoContext.trim() || "";
      if (attachedFiles.length > 0) {
        context += "\n\nAttached files:\n" + attachedFiles.map((f) => `--- ${f.name} (${f.type}) ---\n${f.content}`).join("\n\n");
      }
      const res = await generatePlan(
        description.trim(),
        context || undefined,
        constraints.trim() || undefined,
        activeRepoId ?? undefined,
      );
      setPlan(res.plan);
      setPhases(res.phases);
      setTokensUsed(res.tokens_used);
      setModelUsed(res.model || selectedModel);
      await saveContext(contextPageFor("workspace", projectKey), "last_plan", res.plan).catch(() => {});
      await saveContext(contextPageFor("plan", projectKey), "repo_context", context).catch(() => {});
      await saveContext(contextPageFor("plan", projectKey), "project_description", description.trim()).catch(() => {});
    } catch (e) {
      setError(e instanceof Error ? e.message : "Plan generation failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!plan) return;
    await navigator.clipboard.writeText(plan);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleOpenBuild = async () => {
    if (!plan) return;
    await saveContext(contextPageFor("workspace", projectKey), "last_plan", plan).catch(() => {});
    navigate("/build", { state: { planStep: plan.slice(0, 6000) } });
  };

  const handleOpenMentrix = async () => {
    if (!plan) return;
    await saveContext(contextPageFor("workspace", projectKey), "last_plan", plan).catch(() => {});
    navigate("/mentrix", {
      state: {
        goal: plan.slice(0, 4000),
        projectKey: projectKey || undefined,
        workspace: localPath || undefined,
      },
    });
  };

  return (
    <div className="flex gap-4">
      {/* Conversation History Sidebar */}
      <ConversationHistory mode="plan" className="hidden lg:flex shrink-0" />

      <div className="flex-1 space-y-6 min-w-0">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <ClipboardList size={24} className="text-indigo-600" />
          Plan Mode
        </h1>
        <p className="text-gray-500 mt-1">
          Generate a detailed, phased engineering plan for any project or feature.
        </p>
        {projectKey && (
          <p className="text-xs text-teal-600 mt-1 font-mono" data-testid="plan-workspace-key">
            {projectKey}
          </p>
        )}
      </div>

      {/* Prompt Hygiene Tips */}
      <PromptHygieneTips mode="plan" />

      {/* Input */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <ModelSelector value={selectedModel} onChange={setSelectedModel} />
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Project / Feature Description
          </label>
          <textarea
            data-testid="plan-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe the project or feature you want to plan. Be as specific as possible — include goals, scope, and tech stack preferences..."
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 h-32 resize-none"
          />
        </div>

        {/* Context Files Bar */}
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setShowAddPanel(!showAddPanel)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-indigo-600 bg-indigo-50 border border-indigo-200 rounded-lg hover:bg-indigo-100 transition"
          >
            <Plus size={12} />
            Add files, repos, snippets
          </button>
          {attachedFiles.map((file) => (
            <div key={file.id} className="flex items-center gap-1 px-2 py-1 bg-slate-100 border border-slate-200 rounded-lg text-xs">
              {file.type === "file" && <FileText className="h-3 w-3 text-blue-500" />}
              {file.type === "repo" && <FolderGit2 className="h-3 w-3 text-green-500" />}
              {file.type === "snippet" && <FileCode className="h-3 w-3 text-purple-500" />}
              <span className="text-slate-700 max-w-[100px] truncate">{file.name}</span>
              <button onClick={() => handleRemoveFile(file.id)} className="text-slate-400 hover:text-red-500">
                <X className="h-3 w-3" />
              </button>
            </div>
          ))}
        </div>

        {/* Add File Panel */}
        {showAddPanel && (
          <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
            {/* Browse files from system */}
            <div className="flex items-center gap-3 pb-3 border-b border-slate-200">
              <input
                ref={fileInputRef}
                type="file"
                multiple
                onChange={handleBrowseFiles}
                className="hidden"
                accept="*/*"
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-xs rounded-lg font-medium hover:bg-indigo-700 transition"
              >
                <Upload className="h-3.5 w-3.5" />
                Browse Files from System
              </button>
              <span className="text-[11px] text-slate-500">Select files from your local machine</span>
            </div>

            {/* Manual entry */}
            <p className="text-[11px] text-slate-500 font-medium uppercase tracking-wide">Or add manually:</p>
            <div className="flex gap-2">
              {(["file", "repo", "snippet"] as const).map((type) => (
                <button
                  key={type}
                  onClick={() => setNewFileType(type)}
                  className={`px-3 py-1.5 text-xs rounded-lg font-medium transition flex items-center gap-1 ${
                    newFileType === type
                      ? "bg-indigo-100 text-indigo-700 border border-indigo-300"
                      : "bg-white text-slate-600 border border-slate-200 hover:border-indigo-300"
                  }`}
                >
                  {type === "file" && <FileText className="h-3 w-3" />}
                  {type === "repo" && <FolderGit2 className="h-3 w-3" />}
                  {type === "snippet" && <FileCode className="h-3 w-3" />}
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </button>
              ))}
            </div>
            <input
              type="text"
              value={newFileName}
              onChange={(e) => setNewFileName(e.target.value)}
              placeholder={newFileType === "file" ? "File path (e.g., src/utils/auth.ts)" : newFileType === "repo" ? "Repo URL or owner/repo" : "Snippet name"}
              className="w-full p-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-indigo-500"
            />
            <textarea
              value={newFileContent}
              onChange={(e) => setNewFileContent(e.target.value)}
              placeholder="Paste file content, code snippet, or repo description here..."
              className="w-full h-24 p-2 border border-slate-300 rounded-lg text-xs font-mono focus:ring-2 focus:ring-indigo-500 resize-none"
            />
            <div className="flex gap-2">
              <button onClick={handleAddFile} disabled={!newFileName.trim() || !newFileContent.trim()} className="px-3 py-1.5 bg-indigo-600 text-white text-xs rounded-lg font-medium hover:bg-indigo-700 disabled:bg-slate-300 transition">
                Add Context
              </button>
              <button onClick={() => setShowAddPanel(false)} className="px-3 py-1.5 bg-slate-200 text-slate-600 text-xs rounded-lg font-medium hover:bg-slate-300 transition">
                Cancel
              </button>
            </div>
          </div>
        )}

        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-sm text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
        >
          <Zap size={14} />
          {showAdvanced ? "Hide" : "Show"} advanced options
        </button>

        {showAdvanced && (
          <div className="space-y-3">
            <div>
              <div className="flex items-center justify-between gap-2 mb-1">
                <label className="block text-sm font-medium text-gray-700">
                  Repo Context (optional)
                </label>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    data-testid="plan-clear-context"
                    onClick={() => {
                      void (async () => {
                        setRepoContext("");
                        await clearBlueprintContext();
                        await clearContext("plan").catch(() => {});
                      })();
                    }}
                    className="text-[11px] text-slate-500 hover:text-red-600 underline"
                  >
                    Clear context
                  </button>
                  <button
                    type="button"
                    data-testid="plan-reload-blueprint"
                    onClick={() => {
                      void (async () => {
                        const prompt = await loadBlueprintPrompt(false);
                        if (prompt) {
                          setRepoContext(prompt);
                          setShowAdvanced(true);
                        }
                      })();
                    }}
                    className="text-[11px] text-teal-700 hover:text-teal-900 underline"
                  >
                    Reload from Lattice
                  </button>
                </div>
              </div>
              <textarea
                data-testid="plan-repo-context"
                value={repoContext}
                onChange={(e) => setRepoContext(e.target.value)}
                placeholder="Paste repo analysis or README content for context-aware planning..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 h-20 resize-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Constraints (optional)
              </label>
              <textarea
                value={constraints}
                onChange={(e) => setConstraints(e.target.value)}
                placeholder="Budget limits, timeline, team size, tech restrictions..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 h-16 resize-none"
              />
            </div>
          </div>
        )}

        <button
          data-testid="plan-generate"
          onClick={handleGenerate}
          disabled={loading}
          className="px-5 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2"
        >
          {loading ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <ClipboardList size={16} />
          )}
          {loading ? "Generating Plan..." : "Generate Engineering Plan"}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center gap-3">
          <AlertCircle size={18} className="text-red-500" />
          <span className="text-sm text-red-700">{error}</span>
        </div>
      )}

      {/* Result */}
      {plan && (
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="p-5 border-b border-gray-200 flex items-center justify-between">
            <div>
              <h2 className="font-semibold text-gray-900">Engineering Plan</h2>
              <p className="text-xs text-gray-500">
                {phases.length} phases &middot; ~{tokensUsed.toLocaleString()} tokens{modelUsed ? ` • ${modelUsed}` : ""}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={handleCopy}
              className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition ${
                copied
                  ? "bg-green-100 text-green-700"
                  : "bg-indigo-600 text-white hover:bg-indigo-700"
              }`}
            >
              {copied ? <Check size={16} /> : <Copy size={16} />}
              {copied ? "Copied!" : "Copy Plan"}
            </button>
            <button
              type="button"
              data-testid="plan-open-build"
              onClick={handleOpenBuild}
              className="px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 bg-emerald-600 text-white hover:bg-emerald-700"
            >
              <Hammer size={16} /> Open in Build
            </button>
            <button
              type="button"
              data-testid="plan-open-mentrix"
              onClick={handleOpenMentrix}
              className="px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 border border-teal-600 text-teal-700 hover:bg-teal-50"
            >
              Mentrix bugfix <ArrowRight size={16} />
            </button>
            </div>
          </div>

          {/* Phases sidebar */}
          {phases.length > 0 && (
            <div className="p-4 border-b border-gray-200 bg-indigo-50">
              <p className="text-xs font-semibold text-indigo-700 mb-2">PHASES</p>
              <div className="flex flex-wrap gap-2">
                {phases.map((phase, idx) => (
                  <span
                    key={idx}
                    className="px-3 py-1 bg-white border border-indigo-200 rounded-full text-xs text-indigo-700"
                  >
                    {phase}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="p-5">
            <CodeOutput code={plan} language="markdown" title="Engineering Plan" maxHeight="500px" />
          </div>
        </div>
      )}
      </div>
    </div>
  );
}
