import { useRef, useState } from "react";
import { Eye, FileCode, FileText, FolderGit2, Plus, Upload, X } from "lucide-react";
import {
  attachWebUrl,
  getDocumentMarkdown,
  getWebMarkdown,
  uploadDocument,
  type DocumentArtifactInfo,
  type WebArtifactInfo,
} from "@/lib/api";
import { useActiveProject } from "@/contexts/ActiveProjectContext";

export type AttachedFileType = "file" | "repo" | "snippet" | "document" | "web";

export interface AttachedFile {
  id: string;
  name: string;
  type: AttachedFileType;
  content: string;
  /** Document Intelligence provenance (when type === document) */
  documentArtifactId?: number;
  /** Web Intelligence provenance (when type === web) */
  webArtifactId?: number;
  sourceUrl?: string;
  contentSha256?: string;
  contentVersionId?: number | null;
  freshness?: string;
  scope?: string;
  partialCapabilities?: string[];
  tag?: string;
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
  const [docScope, setDocScope] = useState<"USER_PRIVATE" | "PROJECT_SHARED">("USER_PRIVATE");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [previewMd, setPreviewMd] = useState<{ name: string; text: string; meta: string } | null>(null);
  const [webUrl, setWebUrl] = useState("");
  const [webAdapter, setWebAdapter] = useState<"url" | "rss" | "github" | "browser">("url");
  const [confirmBrowser, setConfirmBrowser] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const docInputRef = useRef<HTMLInputElement>(null);
  const { activeProjectId } = useActiveProject();

  const handleAddFile = () => {
    if (!newFileName.trim() || !newFileContent.trim()) return;
    onChange((prev) => [
      ...prev,
      {
        id: Date.now().toString(),
        name: newFileName.trim(),
        type: newFileType === "document" ? "file" : newFileType,
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

  const attachArtifact = (art: DocumentArtifactInfo, markdownPreview: string) => {
    onChange((prev) => [
      ...prev.filter((f) => f.documentArtifactId !== art.id),
      {
        id: `doc-${art.id}`,
        name: art.filename,
        type: "document",
        content: markdownPreview.slice(0, 4000) || `[Document ${art.filename} sha=${art.content_sha256.slice(0, 12)}]`,
        documentArtifactId: art.id,
        contentSha256: art.content_sha256,
        contentVersionId: art.content_version_id,
        freshness: art.is_current ? "current" : "stale",
        scope: art.scope,
        partialCapabilities: art.partial_capabilities || [],
      },
    ]);
  };

  const handleUploadDocument = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const picked = e.target.files?.[0];
    e.target.value = "";
    if (!picked) return;
    if (docScope === "PROJECT_SHARED" && activeProjectId == null) {
      setUploadError("Select an active project before uploading PROJECT_SHARED documents.");
      return;
    }
    setUploading(true);
    setUploadError("");
    try {
      const res = await uploadDocument({
        file: picked,
        projectId: docScope === "PROJECT_SHARED" ? activeProjectId : activeProjectId,
        scope: docScope,
      });
      const art = res.artifact;
      let md = "";
      try {
        const m = await getDocumentMarkdown(art.id);
        md = m.markdown || "";
      } catch {
        md = "";
      }
      attachArtifact(art, md);
      setShowAddPanel(false);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleRemoveFile = (file: AttachedFile) => {
    // Detach from local context only — do not supersede shared/remote artifacts.
    onChange((prev) => prev.filter((f) => f.id !== file.id));
  };

  const attachWebArtifact = (art: WebArtifactInfo, markdownPreview: string) => {
    onChange((prev) => [
      ...prev.filter((f) => f.webArtifactId !== art.id),
      {
        id: `web-${art.id}`,
        name: art.title || art.source_url,
        type: "web",
        content:
          markdownPreview.slice(0, 4000) ||
          `[Web ${art.source_url} sha=${(art.content_sha256 || "").slice(0, 12)}]`,
        webArtifactId: art.id,
        sourceUrl: art.source_url,
        contentSha256: art.content_sha256,
        contentVersionId: art.content_version_id,
        freshness: art.is_current ? "current" : "stale",
        scope: art.scope,
        partialCapabilities: art.partial_capabilities || [],
        tag: art.tag || "UNTRUSTED_EXTERNAL_CONTEXT",
      },
    ]);
  };

  const handleAttachUrl = async () => {
    if (!webUrl.trim()) return;
    if (docScope === "PROJECT_SHARED" && activeProjectId == null) {
      setUploadError("Select an active project before attaching PROJECT_SHARED URLs.");
      return;
    }
    if (webAdapter === "browser" && !confirmBrowser) {
      setUploadError("Browser snapshot requires explicit confirmation.");
      return;
    }
    setUploading(true);
    setUploadError("");
    try {
      const res = await attachWebUrl({
        url: webUrl.trim(),
        projectId: docScope === "PROJECT_SHARED" ? activeProjectId : activeProjectId,
        scope: docScope,
        adapter: webAdapter,
        confirmedBrowser: confirmBrowser,
      });
      const art = res.artifact;
      let md = "";
      try {
        const m = await getWebMarkdown(art.id);
        md = m.markdown || "";
      } catch {
        md = "";
      }
      attachWebArtifact(art, md);
      setWebUrl("");
      setConfirmBrowser(false);
      setShowAddPanel(false);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Attach URL failed");
    } finally {
      setUploading(false);
    }
  };

  const handlePreviewDocument = async (file: AttachedFile) => {
    try {
      if (file.type === "document" && file.documentArtifactId) {
        const m = await getDocumentMarkdown(file.documentArtifactId);
        setPreviewMd({
          name: file.name,
          text: m.markdown,
          meta: `sha=${(m.content_sha256 || "").slice(0, 12)} · ${m.freshness} · v${m.content_version_id ?? "?"} · ${m.tag}`,
        });
        return;
      }
      if (file.type === "web" && file.webArtifactId) {
        const m = await getWebMarkdown(file.webArtifactId);
        setPreviewMd({
          name: file.name,
          text: m.markdown,
          meta: `url=${m.source_url} · sha=${(m.content_sha256 || "").slice(0, 12)} · ${m.freshness} · ${m.tag}`,
        });
      }
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Preview failed");
    }
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
          Add files, repos, snippets, documents, URLs
        </button>
        {files.map((file) => (
          <div
            key={file.id}
            className="flex items-center gap-1 px-2 py-1 bg-slate-100 border border-slate-200 rounded-lg text-xs"
            title={
              file.type === "document" || file.type === "web"
                ? `${file.freshness || "current"} · ${(file.contentSha256 || "").slice(0, 12)} · ${file.sourceUrl || file.scope || ""}`
                : undefined
            }
          >
            {file.type === "file" && <FileText className="h-3 w-3 text-blue-500" />}
            {file.type === "repo" && <FolderGit2 className="h-3 w-3 text-green-500" />}
            {file.type === "snippet" && <FileCode className="h-3 w-3 text-purple-500" />}
            {file.type === "document" && <FileText className="h-3 w-3 text-teal-600" />}
            {file.type === "web" && <FileText className="h-3 w-3 text-orange-600" />}
            <span className="text-slate-700 max-w-[100px] truncate">{file.name}</span>
            {(file.type === "document" || file.type === "web") && (
              <>
                <span className="text-[10px] text-teal-700">{file.freshness || "current"}</span>
                <button
                  type="button"
                  onClick={() => handlePreviewDocument(file)}
                  className="text-slate-400 hover:text-teal-600"
                  title="View markdown"
                >
                  <Eye className="h-3 w-3" />
                </button>
              </>
            )}
            <button
              type="button"
              onClick={() => handleRemoveFile(file)}
              className="text-slate-400 hover:text-red-500"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        ))}
      </div>

      {uploadError && (
        <p className="mt-2 text-[11px] text-red-600" data-testid="document-upload-error">
          {uploadError}
        </p>
      )}

      {previewMd && (
        <div className="mt-3 p-3 bg-white border border-slate-200 rounded-xl max-h-48 overflow-auto">
          <div className="flex items-center justify-between gap-2 mb-2">
            <div>
              <p className="text-xs font-medium text-slate-800">{previewMd.name}</p>
              <p className="text-[10px] text-slate-500">{previewMd.meta}</p>
            </div>
            <button type="button" className="text-xs text-slate-500" onClick={() => setPreviewMd(null)}>
              Close
            </button>
          </div>
          <pre className="text-[11px] whitespace-pre-wrap font-mono text-slate-700">{previewMd.text}</pre>
        </div>
      )}

      {showAddPanel && (
        <div className="mt-3 p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
          <div className="flex items-center gap-3 pb-3 border-b border-slate-200 flex-wrap">
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
            <input
              ref={docInputRef}
              type="file"
              onChange={handleUploadDocument}
              className="hidden"
              accept=".txt,.md,.markdown,.docx,.pdf,.pptx"
              data-testid="document-upload-input"
            />
            <button
              type="button"
              disabled={uploading}
              onClick={() => docInputRef.current?.click()}
              className="flex items-center gap-2 px-4 py-2 text-xs rounded-lg font-medium border border-teal-300 bg-teal-50 text-teal-800 hover:bg-teal-100 disabled:opacity-50"
              data-testid="document-upload-button"
            >
              <Upload className="h-3.5 w-3.5" />
              {uploading ? "Uploading…" : "Upload Document"}
            </button>
            <select
              value={docScope}
              onChange={(e) => setDocScope(e.target.value as "USER_PRIVATE" | "PROJECT_SHARED")}
              className="text-xs border border-slate-300 rounded-lg px-2 py-1.5 bg-white"
              data-testid="document-scope-select"
            >
              <option value="USER_PRIVATE">USER_PRIVATE</option>
              <option value="PROJECT_SHARED">PROJECT_SHARED</option>
            </select>
            <span className="text-[11px] text-slate-500">Parsed docs reuse Knowledge + ContextPack provenance</span>
          </div>

          <div className="flex flex-col gap-2 pb-3 border-b border-slate-200">
            <p className="text-[11px] text-slate-500 font-medium uppercase tracking-wide">
              Attach URL (UNTRUSTED_EXTERNAL_CONTEXT)
            </p>
            <div className="flex flex-wrap gap-2 items-center">
              <input
                type="url"
                value={webUrl}
                onChange={(e) => setWebUrl(e.target.value)}
                placeholder="https://…"
                className={`flex-1 min-w-[200px] p-2 border border-slate-300 rounded-lg text-xs focus:ring-2 ${styles.focusRing}`}
                data-testid="web-url-input"
              />
              <select
                value={webAdapter}
                onChange={(e) => setWebAdapter(e.target.value as typeof webAdapter)}
                className="text-xs border border-slate-300 rounded-lg px-2 py-1.5 bg-white"
                data-testid="web-adapter-select"
              >
                <option value="url">URL</option>
                <option value="rss">RSS/Atom</option>
                <option value="github">GitHub</option>
                <option value="browser">Browser snapshot</option>
              </select>
              {webAdapter === "browser" && (
                <label className="text-[11px] text-slate-600 flex items-center gap-1">
                  <input
                    type="checkbox"
                    checked={confirmBrowser}
                    onChange={(e) => setConfirmBrowser(e.target.checked)}
                    data-testid="web-browser-confirm"
                  />
                  Confirm browser fetch
                </label>
              )}
              <button
                type="button"
                disabled={uploading || !webUrl.trim()}
                onClick={handleAttachUrl}
                className="flex items-center gap-2 px-4 py-2 text-xs rounded-lg font-medium border border-orange-300 bg-orange-50 text-orange-900 hover:bg-orange-100 disabled:opacity-50"
                data-testid="web-attach-button"
              >
                {uploading ? "Fetching…" : "Attach URL"}
              </button>
            </div>
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
