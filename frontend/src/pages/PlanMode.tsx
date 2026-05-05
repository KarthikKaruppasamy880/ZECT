import { useState, useRef } from "react";
import { generatePlan } from "@/lib/api";
import CodeOutput from "@/components/CodeOutput";
import ModelSelector from "@/components/ModelSelector";
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
} from "lucide-react";

interface AttachedFile {
  id: string;
  name: string;
  type: "file" | "repo" | "snippet";
  content: string;
}

export default function PlanMode() {
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
        constraints.trim() || undefined
      );
      setPlan(res.plan);
      setPhases(res.phases);
      setTokensUsed(res.tokens_used);
      setModelUsed(res.model || selectedModel);
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <ClipboardList size={24} className="text-indigo-600" />
          Plan Mode
        </h1>
        <p className="text-gray-500 mt-1">
          Generate a detailed, phased engineering plan for any project or feature.
        </p>
      </div>

      {/* Input */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <ModelSelector value={selectedModel} onChange={setSelectedModel} />
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Project / Feature Description
          </label>
          <textarea
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
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Repo Context (optional)
              </label>
              <textarea
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
  );
}
