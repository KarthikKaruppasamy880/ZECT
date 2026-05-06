import { useState, useEffect } from "react";
import {
  FolderOpen,
  File,
  FileText,
  ChevronRight,
  Search,
  Save,
  Trash2,
  Edit3,
  RefreshCw,
  Loader2,
  Info,
  FilePlus,
  Eye,
  Code2,
  Home,
} from "lucide-react";
import { fileList, fileRead, fileWrite, fileCreate, fileDelete, fileSearch, fileTree } from "@/lib/api";

interface FileEntry {
  name: string;
  path: string;
  is_dir: boolean;
  size: number;
  modified: string;
  language?: string;
  children?: FileEntry[];
}

interface FileContent {
  path: string;
  content: string;
  size: number;
  lines: number;
  language: string;
}

export default function FileExplorer() {
  const [showGuide, setShowGuide] = useState(false);
  const [rootPath] = useState("/home");
  const [_tree, setTree] = useState<FileEntry[]>([]);
  const [selectedFile, setSelectedFile] = useState<FileContent | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [editContent, setEditContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState("");
  const [newFileName, setNewFileName] = useState("");
  const [showNewFile, setShowNewFile] = useState(false);
  const [currentDir, setCurrentDir] = useState("/home");
  const [dirEntries, setDirEntries] = useState<FileEntry[]>([]);

  // Load directory listing
  const loadDir = async (path: string) => {
    setLoading(true);
    setError("");
    try {
      const entries = await fileList(path);
      setDirEntries(entries);
      setCurrentDir(path);
    } catch (err: any) {
      setError(err.message);
    }
    setLoading(false);
  };

  // Load tree
  const loadTree = async () => {
    setLoading(true);
    setError("");
    try {
      const t = await fileTree(rootPath, 2);
      setTree(t);
    } catch (err: any) {
      setError(err.message);
    }
    setLoading(false);
  };

  useEffect(() => {
    loadDir(currentDir);
    loadTree();
  }, []);

  // Open file
  const openFile = async (path: string) => {
    setLoading(true);
    setError("");
    setEditMode(false);
    try {
      const content = await fileRead(path);
      setSelectedFile(content);
      setEditContent(content.content);
    } catch (err: any) {
      setError(err.message);
    }
    setLoading(false);
  };

  // Save file
  const saveFile = async () => {
    if (!selectedFile) return;
    setSaving(true);
    setError("");
    try {
      await fileWrite(selectedFile.path, editContent);
      setSelectedFile({ ...selectedFile, content: editContent });
      setEditMode(false);
    } catch (err: any) {
      setError(err.message);
    }
    setSaving(false);
  };

  // Create file
  const createNewFile = async () => {
    if (!newFileName.trim()) return;
    setSaving(true);
    setError("");
    const fullPath = `${currentDir}/${newFileName}`.replace(/\/+/g, "/");
    try {
      await fileCreate(fullPath);
      setNewFileName("");
      setShowNewFile(false);
      loadDir(currentDir);
    } catch (err: any) {
      setError(err.message);
    }
    setSaving(false);
  };

  // Delete file
  const deleteFile = async (path: string) => {
    if (!confirm(`Delete ${path}?`)) return;
    setError("");
    try {
      await fileDelete(path);
      if (selectedFile?.path === path) {
        setSelectedFile(null);
      }
      loadDir(currentDir);
    } catch (err: any) {
      setError(err.message);
    }
  };

  // Search
  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    setError("");
    try {
      const results = await fileSearch(currentDir, searchQuery);
      setSearchResults(results);
    } catch (err: any) {
      setError(err.message);
    }
    setSearching(false);
  };

  // Navigate to directory
  const navigateToDir = (path: string) => {
    loadDir(path);
  };

  // Breadcrumb parts
  const breadcrumbs = currentDir.split("/").filter(Boolean);

  // Language icon color
  const langColor = (lang: string) => {
    const colors: Record<string, string> = {
      python: "text-yellow-600",
      javascript: "text-yellow-500",
      typescript: "text-blue-600",
      html: "text-orange-500",
      css: "text-blue-500",
      json: "text-green-600",
      markdown: "text-slate-600",
      yaml: "text-red-500",
    };
    return colors[lang] || "text-slate-500";
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <FolderOpen className="h-6 w-6 text-amber-600" />
            File Explorer
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Browse, read, write, and search files directly on the server
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => loadDir(currentDir)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-slate-100 text-slate-600 hover:bg-slate-200 transition-colors"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
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
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 space-y-3">
          <h3 className="font-semibold text-amber-900">File Explorer — Direct File System Access</h3>
          <div className="text-sm text-amber-800 space-y-2">
            <p>
              <strong>Browse</strong> — Navigate the server file system. Click folders to open them, files to view their contents.
            </p>
            <p>
              <strong>Edit</strong> — Click the Edit button on any file to modify its contents directly. Save changes with one click.
            </p>
            <p>
              <strong>Search</strong> — Search for text patterns across files in the current directory using grep-like search.
            </p>
            <p>
              <strong>Create / Delete</strong> — Create new files or delete existing ones from the toolbar.
            </p>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
          {error}
          <button onClick={() => setError("")} className="ml-2 text-red-500 hover:text-red-700 font-medium">
            Dismiss
          </button>
        </div>
      )}

      {/* Search + Breadcrumb bar */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-4 space-y-3">
        {/* Breadcrumbs */}
        <div className="flex items-center gap-1 text-sm overflow-x-auto">
          <button
            onClick={() => navigateToDir("/")}
            className="text-slate-500 hover:text-slate-700 p-1"
          >
            <Home className="h-4 w-4" />
          </button>
          {breadcrumbs.map((part, i) => {
            const path = "/" + breadcrumbs.slice(0, i + 1).join("/");
            return (
              <span key={path} className="flex items-center gap-1">
                <ChevronRight className="h-3 w-3 text-slate-400" />
                <button
                  onClick={() => navigateToDir(path)}
                  className={`px-1.5 py-0.5 rounded hover:bg-slate-100 ${
                    i === breadcrumbs.length - 1 ? "font-medium text-slate-900" : "text-slate-500"
                  }`}
                >
                  {part}
                </button>
              </span>
            );
          })}
        </div>

        {/* Search bar */}
        <div className="flex items-center gap-2">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search files by content..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              className="w-full pl-9 pr-3 py-2 border border-slate-200 rounded-lg text-sm focus:border-amber-500 focus:ring-1 focus:ring-amber-500 outline-none"
            />
          </div>
          <button
            onClick={handleSearch}
            disabled={searching || !searchQuery.trim()}
            className="px-4 py-2 bg-amber-600 text-white text-sm rounded-lg hover:bg-amber-700 disabled:opacity-50 flex items-center gap-1.5"
          >
            {searching ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            Search
          </button>
          <button
            onClick={() => setShowNewFile(!showNewFile)}
            className="px-3 py-2 bg-slate-100 text-slate-600 text-sm rounded-lg hover:bg-slate-200 flex items-center gap-1.5"
          >
            <FilePlus className="h-4 w-4" />
            New File
          </button>
        </div>

        {/* New file input */}
        {showNewFile && (
          <div className="flex items-center gap-2 bg-slate-50 rounded-lg p-3">
            <span className="text-sm text-slate-500 font-mono">{currentDir}/</span>
            <input
              type="text"
              placeholder="filename.ext"
              value={newFileName}
              onChange={(e) => setNewFileName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && createNewFile()}
              className="flex-1 px-3 py-1.5 border border-slate-200 rounded text-sm focus:border-amber-500 outline-none"
              autoFocus
            />
            <button
              onClick={createNewFile}
              disabled={saving || !newFileName.trim()}
              className="px-3 py-1.5 bg-amber-600 text-white text-sm rounded hover:bg-amber-700 disabled:opacity-50"
            >
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : "Create"}
            </button>
            <button
              onClick={() => { setShowNewFile(false); setNewFileName(""); }}
              className="px-3 py-1.5 text-slate-500 text-sm hover:text-slate-700"
            >
              Cancel
            </button>
          </div>
        )}
      </div>

      {/* Search results */}
      {searchResults.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
            <h3 className="font-semibold text-slate-900 text-sm">
              Search Results ({searchResults.length})
            </h3>
            <button
              onClick={() => setSearchResults([])}
              className="text-xs text-slate-400 hover:text-slate-600"
            >
              Clear
            </button>
          </div>
          <div className="divide-y divide-slate-100 max-h-60 overflow-y-auto">
            {searchResults.map((result: any, i: number) => (
              <div
                key={i}
                className="px-4 py-2 hover:bg-slate-50 cursor-pointer"
                onClick={() => openFile(result.file || result.path)}
              >
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-amber-500" />
                  <span className="text-sm font-medium text-slate-700 truncate">
                    {result.file || result.path}
                  </span>
                  {result.line_number && (
                    <span className="text-xs text-slate-400">Line {result.line_number}</span>
                  )}
                </div>
                {result.line && (
                  <p className="text-xs text-slate-500 mt-1 font-mono truncate pl-6">{result.line}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Main content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Directory listing */}
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
            <h3 className="font-semibold text-slate-900 text-sm flex items-center gap-2">
              <FolderOpen className="h-4 w-4 text-amber-600" />
              Files
            </h3>
            <button onClick={() => navigateToDir(currentDir.split("/").slice(0, -1).join("/") || "/")} className="text-xs text-slate-400 hover:text-slate-600">
              Up
            </button>
          </div>

          <div className="divide-y divide-slate-50 max-h-[500px] overflow-y-auto">
            {loading && dirEntries.length === 0 ? (
              <div className="p-8 text-center text-slate-400">
                <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2" />
                <p className="text-sm">Loading...</p>
              </div>
            ) : dirEntries.length === 0 ? (
              <div className="p-8 text-center text-slate-400">
                <FolderOpen className="h-8 w-8 mx-auto mb-2 opacity-40" />
                <p className="text-sm">Empty directory</p>
              </div>
            ) : (
              dirEntries.map((entry) => (
                <div
                  key={entry.path}
                  className={`px-4 py-2.5 hover:bg-slate-50 cursor-pointer flex items-center justify-between group ${
                    selectedFile?.path === entry.path ? "bg-amber-50 border-l-2 border-amber-500" : ""
                  }`}
                  onClick={() => {
                    if (entry.is_dir) {
                      navigateToDir(entry.path);
                    } else {
                      openFile(entry.path);
                    }
                  }}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    {entry.is_dir ? (
                      <FolderOpen className="h-4 w-4 text-amber-500 shrink-0" />
                    ) : (
                      <File className={`h-4 w-4 shrink-0 ${langColor(entry.language || "")}`} />
                    )}
                    <span className="text-sm text-slate-700 truncate">{entry.name}</span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                    {!entry.is_dir && (
                      <>
                        <span className="text-xs text-slate-400">{formatSize(entry.size)}</span>
                        <button
                          onClick={(e) => { e.stopPropagation(); deleteFile(entry.path); }}
                          className="p-1 text-red-400 hover:text-red-600 rounded"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right: File viewer/editor */}
        <div className="lg:col-span-2">
          {selectedFile ? (
            <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
                <div className="flex items-center gap-2 min-w-0">
                  <Code2 className={`h-4 w-4 ${langColor(selectedFile.language)}`} />
                  <span className="text-sm font-medium text-slate-900 truncate">{selectedFile.path}</span>
                  <span className="text-xs text-slate-400">{selectedFile.language}</span>
                  <span className="text-xs text-slate-400">{selectedFile.lines} lines</span>
                  <span className="text-xs text-slate-400">{formatSize(selectedFile.size)}</span>
                </div>
                <div className="flex items-center gap-2">
                  {editMode ? (
                    <>
                      <button
                        onClick={saveFile}
                        disabled={saving}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-600 text-white text-sm rounded-lg hover:bg-amber-700 disabled:opacity-50"
                      >
                        {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
                        Save
                      </button>
                      <button
                        onClick={() => { setEditMode(false); setEditContent(selectedFile.content); }}
                        className="px-3 py-1.5 text-slate-500 text-sm hover:text-slate-700"
                      >
                        Cancel
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={() => setEditMode(true)}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 text-slate-600 text-sm rounded-lg hover:bg-slate-200"
                      >
                        <Edit3 className="h-3.5 w-3.5" />
                        Edit
                      </button>
                      <button
                        onClick={() => openFile(selectedFile.path)}
                        className="p-1.5 text-slate-400 hover:text-slate-600 rounded"
                      >
                        <RefreshCw className="h-3.5 w-3.5" />
                      </button>
                    </>
                  )}
                </div>
              </div>

              {editMode ? (
                <textarea
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  className="w-full h-[500px] p-4 font-mono text-sm text-slate-800 bg-slate-50 border-0 outline-none resize-none"
                  spellCheck={false}
                />
              ) : (
                <div className="h-[500px] overflow-auto">
                  <pre className="p-4 font-mono text-sm text-slate-800 bg-slate-50 whitespace-pre-wrap">
                    {selectedFile.content.split("\n").map((line, i) => (
                      <div key={i} className="flex hover:bg-amber-50">
                        <span className="w-12 text-right pr-4 text-slate-400 select-none shrink-0">{i + 1}</span>
                        <span className="flex-1">{line || "\u00A0"}</span>
                      </div>
                    ))}
                  </pre>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-12 text-center">
              <Eye className="h-12 w-12 mx-auto mb-3 text-slate-300" />
              <p className="text-slate-500">Select a file to view its contents</p>
              <p className="text-xs text-slate-400 mt-1">Click any file in the left panel to open it</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
