import { useState } from "react";
import {
  Code2, Search, Database, FileCode, Braces, Hash, RefreshCw,
} from "lucide-react";
import { searchCodeSymbols, indexRepo, getCodeIndexStats } from "@/lib/api";

const SYMBOL_TYPES = ["", "function", "class", "variable", "import", "interface", "type", "method"];
const LANGUAGES = ["", "python", "typescript", "javascript", "java", "go", "rust", "ruby", "c", "cpp"];

export default function CodeIndex() {
  const [query, setQuery] = useState("");
  const [symbolType, setSymbolType] = useState("");
  const [language, setLanguage] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [searching, setSearching] = useState(false);
  const [indexing, setIndexing] = useState(false);
  const [error, setError] = useState("");
  const [indexPath, setIndexPath] = useState("");
  const [showIndex, setShowIndex] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;
    try {
      setSearching(true);
      setError("");
      const res = await searchCodeSymbols(query, symbolType || undefined, language || undefined);
      setResults(res || []);
    } catch (e: any) {
      setError(e.message || "Search failed");
    } finally {
      setSearching(false);
    }
  };

  const handleIndex = async () => {
    if (!indexPath.trim()) return;
    try {
      setIndexing(true);
      setError("");
      const res = await indexRepo(indexPath);
      setShowIndex(false);
      setIndexPath("");
      alert(`Indexed ${res.symbols_found || 0} symbols from ${res.files_processed || 0} files`);
      loadStats();
    } catch (e: any) {
      setError(e.message || "Indexing failed");
    } finally {
      setIndexing(false);
    }
  };

  const loadStats = async () => {
    try {
      const res = await getCodeIndexStats();
      setStats(res);
    } catch {
      // silently fail stats load
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Code2 className="h-6 w-6 text-cyan-600" /> Code Index
          </h1>
          <p className="text-sm text-slate-500 mt-1">Search functions, classes, variables across your codebase</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={loadStats}
            className="flex items-center gap-1.5 px-3 py-2 border border-slate-300 text-slate-600 rounded-lg hover:bg-slate-50 text-sm"
          >
            <Database className="h-4 w-4" /> Stats
          </button>
          <button
            onClick={() => setShowIndex(!showIndex)}
            className="flex items-center gap-1.5 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 text-sm"
          >
            <RefreshCw className="h-4 w-4" /> Index Repo
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">{error}</div>
      )}

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-cyan-50 rounded-xl p-4">
            <p className="text-xs text-slate-500">Total Symbols</p>
            <p className="text-2xl font-bold text-slate-900">{stats.total_symbols || 0}</p>
          </div>
          <div className="bg-cyan-50 rounded-xl p-4">
            <p className="text-xs text-slate-500">Languages</p>
            <p className="text-2xl font-bold text-slate-900">{stats.languages || 0}</p>
          </div>
          <div className="bg-cyan-50 rounded-xl p-4">
            <p className="text-xs text-slate-500">Repos Indexed</p>
            <p className="text-2xl font-bold text-slate-900">{stats.repos_indexed || 0}</p>
          </div>
          <div className="bg-cyan-50 rounded-xl p-4">
            <p className="text-xs text-slate-500">Breakdown</p>
            <div className="flex flex-wrap gap-1 mt-1">
              {stats.by_type && Object.entries(stats.by_type).map(([k, v]) => (
                <span key={k} className="text-xs bg-white px-1.5 py-0.5 rounded text-slate-600">{k}: {v as number}</span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Index Form */}
      {showIndex && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4 shadow-sm">
          <h3 className="font-semibold text-slate-900">Index a Repository</h3>
          <div className="flex gap-3">
            <input
              type="text"
              placeholder="Path to repository (e.g. /home/ubuntu/repos/ZECT)"
              value={indexPath}
              onChange={e => setIndexPath(e.target.value)}
              className="flex-1 px-4 py-2 border border-slate-300 rounded-lg text-sm font-mono"
            />
            <button
              onClick={handleIndex}
              disabled={!indexPath.trim() || indexing}
              className="flex items-center gap-1.5 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 text-sm disabled:opacity-50"
            >
              {indexing ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Database className="h-4 w-4" />}
              {indexing ? "Indexing..." : "Start Index"}
            </button>
          </div>
        </div>
      )}

      {/* Search */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search symbols (functions, classes, variables)..."
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleSearch()}
              className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg text-sm"
            />
          </div>
          <select
            value={symbolType}
            onChange={e => setSymbolType(e.target.value)}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
          >
            <option value="">All Types</option>
            {SYMBOL_TYPES.filter(Boolean).map(t => (
              <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
            ))}
          </select>
          <select
            value={language}
            onChange={e => setLanguage(e.target.value)}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
          >
            <option value="">All Languages</option>
            {LANGUAGES.filter(Boolean).map(l => (
              <option key={l} value={l}>{l.charAt(0).toUpperCase() + l.slice(1)}</option>
            ))}
          </select>
          <button
            onClick={handleSearch}
            disabled={!query.trim() || searching}
            className="flex items-center gap-1.5 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 text-sm disabled:opacity-50"
          >
            {searching ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            Search
          </button>
        </div>
      </div>

      {/* Results */}
      {results.length > 0 ? (
        <div className="space-y-2">
          <p className="text-sm text-slate-500">{results.length} symbols found</p>
          {results.map((r: any, idx: number) => (
            <div key={idx} className="bg-white border border-slate-200 rounded-xl p-4 hover:shadow-sm transition-shadow">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <SymbolIcon type={r.symbol_type} />
                    <h3 className="font-semibold text-slate-900 font-mono text-sm">{r.name}</h3>
                    <span className="px-2 py-0.5 bg-cyan-50 text-cyan-600 rounded-full text-xs">{r.symbol_type}</span>
                    <span className="px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full text-xs">{r.language}</span>
                  </div>
                  <p className="text-xs text-slate-500 font-mono truncate">{r.file_path}:{r.line_number}</p>
                  {r.signature && (
                    <pre className="mt-2 text-xs bg-slate-50 p-2 rounded-lg overflow-x-auto text-slate-600 font-mono">{r.signature}</pre>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : query && !searching ? (
        <div className="text-center py-12 text-slate-500">
          <Search className="h-12 w-12 mx-auto mb-3 text-slate-300" />
          <p className="text-lg font-medium">No symbols found</p>
          <p className="text-sm mt-1">Try a different search term or index your repository first</p>
        </div>
      ) : null}
    </div>
  );
}

function SymbolIcon({ type }: { type: string }) {
  switch (type) {
    case "function":
    case "method":
      return <Braces className="h-4 w-4 text-blue-500" />;
    case "class":
    case "interface":
    case "type":
      return <FileCode className="h-4 w-4 text-purple-500" />;
    case "variable":
      return <Hash className="h-4 w-4 text-green-500" />;
    default:
      return <Code2 className="h-4 w-4 text-slate-400" />;
  }
}
