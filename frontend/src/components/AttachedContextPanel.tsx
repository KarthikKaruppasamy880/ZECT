import { useRef, useState } from "react";
import { FileCode, FileText, FolderGit2, Plus, Upload, X } from "lucide-react";

export type AttachedFileType = "file" | "repo" | "snippet";

export interface AttachedFile {
  id: string;
  name: string;
  type: AttachedFileType;
  content: string;
}

type Accent = "blue" | "indigo" | "amber";

const ACCENT: Record<
  Accent,
  {
    chipBtn: string;
    primaryBtn: string;
    typeActive: string;
    focusRing: string;
  }
> = {
  blue: {
    chipBtn:
      "text-blue-600 bg-blue-50 border-blue-200 hover:bg-blue-100",
    primaryBtn: "bg-blue-600 hover:bg-blue-700",
    typeActive: "bg-blue-100 text-blue-700 border-blue-300",
    focusRing: "focus:ring-blue-500",
  },
  indigo: {
    chipBtn:
      "text-indigo-600 bg-indigo-50 border-indigo-200 hover:bg-indigo-100",
    primaryBtn: "bg-indigo-600 hover:bg-indigo-700",
    typeActive: "bg-indigo-100 text-indigo-700 border-indigo-300",
    focusRing: "focus:ring-indigo-500",
  },
  amber: {
    chipBtn:
      "text-amber-700 bg-amber-50 border-amber-200 hover:bg-amber-100",
    primaryBtn: "bg-amber-600 hover:bg-amber-700",
    typeActive: "bg-amber-100 text-amber-800 border-amber-300",
    focusRing: "focus:ring-amber-500",
  },
};

interface AttachedContextPanelProps {
  files: AttachedFile[];
  onChange: React.Dispatch<React.SetStateAction<AttachedFile[]>>;
  accent?: Accent;
  className?: string;
}

/** Shared attach-files chrome for Ask / Plan / Build phase pages. */
export default function AttachedContextPanel({
  files,
  onChange,
  accent = "blue",
  className = "",
}: AttachedContextPanelProps) {
  const styles = ACCENT[accent];
  const [showAddPanel, setShowAddPanel] = useState(false);
  const [newFileName, setNewFileName] = useState("");
  const [newFileContent, setNewFileContent] = useState("");
  const [newFileType, setNewFileType] = useState<AttachedFileType>("file");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleAddFile = () => {
    if (!newFileName.trim() || !newFileContent.trim()) return;
    onChange((prev) => [
      ...prev,
      {
        id: Date.now().toString(),
        name: newFileName.trim(),
        type: newFileType,
        content: newFileContent.trim(),
      },
    ]);
    setNewFileName("");
    setNewFileContent("");
    setShowAddPanel(false);
  };

  const handleBrowseFiles = (e: React.ChangeEvent<HTMLInputElement>) => {
    const picked = e.target.files;
    if (!picked) return;
    Array.from(picked).forEach((file) => {
      const reader = new FileReader();
      reader.onload = (ev) => {
        const content = ev.target?.result as string;
        onChange((prev) => [
          ...prev,
          {
            id: `${Date.now()}-${file.name}`,
            name: file.name,
            type: "file",
            content,
          },
        ]);
      };
      reader.readAsText(file);
    });
    e.target.value = "";
  };

  const handleRemoveFile = (id: string) => {
    onChange((prev) => prev.filter((f) => f.id !== id));
  };

  return (
    <div className={className} data-testid="attached-context-panel">
      <div className="flex items-center gap-2 flex-wrap">
        <button
          type="button"
          onClick={() => setShowAddPanel(!showAddPanel)}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border rounded-lg transition ${styles.chipBtn}`}
        >
          <Plus size={12} />
          Add files, repos, snippets
        </button>
        {files.map((file) => (
          <div
            key={file.id}
            className="flex items-center gap-1 px-2 py-1 bg-slate-100 border border-slate-200 rounded-lg text-xs"
          >
            {file.type === "file" && <FileText className="h-3 w-3 text-blue-500" />}
            {file.type === "repo" && <FolderGit2 className="h-3 w-3 text-green-500" />}
            {file.type === "snippet" && <FileCode className="h-3 w-3 text-purple-500" />}
            <span className="text-slate-700 max-w-[100px] truncate">{file.name}</span>
            <button
              type="button"
              onClick={() => handleRemoveFile(file.id)}
              className="text-slate-400 hover:text-red-500"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        ))}
      </div>

      {showAddPanel && (
        <div className="mt-3 p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
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
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className={`flex items-center gap-2 px-4 py-2 text-white text-xs rounded-lg font-medium transition ${styles.primaryBtn}`}
            >
              <Upload className="h-3.5 w-3.5" />
              Browse Files from System
            </button>
            <span className="text-[11px] text-slate-500">Select files from your local machine</span>
          </div>

          <p className="text-[11px] text-slate-500 font-medium uppercase tracking-wide">
            Or add manually:
          </p>
          <div className="flex gap-2">
            {(["file", "repo", "snippet"] as const).map((type) => (
              <button
                key={type}
                type="button"
                onClick={() => setNewFileType(type)}
                className={`px-3 py-1.5 text-xs rounded-lg font-medium transition flex items-center gap-1 border ${
                  newFileType === type
                    ? styles.typeActive
                    : "bg-white text-slate-600 border-slate-200 hover:border-slate-300"
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
            placeholder={
              newFileType === "file"
                ? "File path (e.g., src/utils/auth.ts)"
                : newFileType === "repo"
                  ? "Repo URL or owner/repo"
                  : "Snippet name"
            }
            className={`w-full p-2 border border-slate-300 rounded-lg text-xs focus:ring-2 ${styles.focusRing}`}
          />
          <textarea
            value={newFileContent}
            onChange={(e) => setNewFileContent(e.target.value)}
            placeholder="Paste file content, code snippet, or repo description here..."
            className={`w-full h-24 p-2 border border-slate-300 rounded-lg text-xs font-mono focus:ring-2 resize-none ${styles.focusRing}`}
          />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleAddFile}
              disabled={!newFileName.trim() || !newFileContent.trim()}
              className={`px-3 py-1.5 text-white text-xs rounded-lg font-medium disabled:bg-slate-300 transition ${styles.primaryBtn}`}
            >
              Add Context
            </button>
            <button
              type="button"
              onClick={() => setShowAddPanel(false)}
              className="px-3 py-1.5 bg-slate-200 text-slate-600 text-xs rounded-lg font-medium hover:bg-slate-300 transition"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
