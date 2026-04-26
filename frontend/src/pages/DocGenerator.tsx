import { useState } from "react";
import { generateDocs } from "@/lib/api";
import type { DocGenResult } from "@/types";
import {
  FileText,
  Loader2,
  AlertCircle,
  Copy,
  Check,
  ChevronDown,
  ChevronRight,
} from "lucide-react";

const AVAILABLE_SECTIONS = [
  { key: "overview", label: "Overview" },
  { key: "architecture", label: "Architecture" },
  { key: "api", label: "API Reference" },
  { key: "setup", label: "Setup Guide" },
  { key: "testing", label: "Testing" },
  { key: "deployment", label: "Deployment" },
];

export default function DocGenerator() {
  const [owner, setOwner] = useState("");
  const [repo, setRepo] = useState("");
  const [selectedSections, setSelectedSections] = useState<string[]>(
    AVAILABLE_SECTIONS.map((s) => s.key)
  );
  const [result, setResult] = useState<DocGenResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedSection, setExpandedSection] = useState<string | null>(null);
  const [copiedSection, setCopiedSection] = useState<string | null>(null);

  const toggleSection = (key: string) => {
    setSelectedSections((prev) =>
      prev.includes(key) ? prev.filter((s) => s !== key) : [...prev, key]
    );
  };

  const handleGenerate = async () => {
    if (!owner.trim() || !repo.trim()) {
      setError("Please enter both owner and repo name.");
      return;
    }
    if (selectedSections.length === 0) {
      setError("Select at least one documentation section.");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await generateDocs(owner.trim(), repo.trim(), selectedSections);
      setResult(data);
      if (data.sections.length > 0) {
        setExpandedSection(data.sections[0].title);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Documentation generation failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleCopySection = async (content: string, title: string) => {
    await navigator.clipboard.writeText(content);
    setCopiedSection(title);
    setTimeout(() => setCopiedSection(null), 2000);
  };

  const handleCopyAll = async () => {
    if (!result) return;
    const full = result.sections.map((s) => s.content).join("\n\n---\n\n");
    await navigator.clipboard.writeText(full);
    setCopiedSection("__all__");
    setTimeout(() => setCopiedSection(null), 2000);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Documentation Generator</h1>
        <p className="text-gray-500 mt-1">
          Generate granular documentation for any GitHub repository — overview, architecture, API
          reference, setup guide, testing, and deployment.
        </p>
      </div>

      {/* Input */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <div className="flex gap-3 items-end">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">Owner</label>
            <input
              type="text"
              value={owner}
              onChange={(e) => setOwner(e.target.value)}
              placeholder="e.g. KarthikKaruppasamy880"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
            />
          </div>
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">Repository</label>
            <input
              type="text"
              value={repo}
              onChange={(e) => setRepo(e.target.value)}
              placeholder="e.g. ZECT"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
            />
          </div>
        </div>

        <div>
          <p className="text-sm font-medium text-gray-700 mb-2">Sections to Generate</p>
          <div className="flex flex-wrap gap-2">
            {AVAILABLE_SECTIONS.map((s) => (
              <button
                key={s.key}
                onClick={() => toggleSection(s.key)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                  selectedSections.includes(s.key)
                    ? "bg-emerald-100 text-emerald-700 border border-emerald-300"
                    : "bg-gray-100 text-gray-500 border border-gray-200"
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={handleGenerate}
          disabled={loading}
          className="px-5 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 disabled:opacity-50 flex items-center gap-2"
        >
          {loading ? <Loader2 size={16} className="animate-spin" /> : <FileText size={16} />}
          Generate Documentation
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
      {result && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Documentation: {result.repo_name}
              </h2>
              <p className="text-xs text-gray-500">
                {result.sections.length} sections &middot; ~{result.total_tokens.toLocaleString()}{" "}
                tokens
              </p>
            </div>
            <button
              onClick={handleCopyAll}
              className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition ${
                copiedSection === "__all__"
                  ? "bg-green-100 text-green-700"
                  : "bg-emerald-600 text-white hover:bg-emerald-700"
              }`}
            >
              {copiedSection === "__all__" ? <Check size={16} /> : <Copy size={16} />}
              {copiedSection === "__all__" ? "Copied All!" : "Copy All Sections"}
            </button>
          </div>

          {result.sections.map((section) => {
            const isExpanded = expandedSection === section.title;
            return (
              <div key={section.title} className="bg-white rounded-xl border border-gray-200">
                <button
                  onClick={() => setExpandedSection(isExpanded ? null : section.title)}
                  className="w-full p-4 flex items-center justify-between text-left"
                >
                  <div className="flex items-center gap-2">
                    {isExpanded ? (
                      <ChevronDown size={16} className="text-gray-400" />
                    ) : (
                      <ChevronRight size={16} className="text-gray-400" />
                    )}
                    <span className="font-medium text-gray-900">{section.title}</span>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleCopySection(section.content, section.title);
                    }}
                    className={`px-3 py-1 rounded text-xs font-medium flex items-center gap-1 transition ${
                      copiedSection === section.title
                        ? "bg-green-100 text-green-700"
                        : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    }`}
                  >
                    {copiedSection === section.title ? (
                      <Check size={12} />
                    ) : (
                      <Copy size={12} />
                    )}
                    {copiedSection === section.title ? "Copied!" : "Copy"}
                  </button>
                </button>
                {isExpanded && (
                  <div className="border-t border-gray-200 p-4">
                    <div className="bg-gray-50 rounded-lg p-4 max-h-80 overflow-y-auto">
                      <pre className="text-xs text-gray-700 font-mono whitespace-pre-wrap">
                        {section.content}
                      </pre>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
