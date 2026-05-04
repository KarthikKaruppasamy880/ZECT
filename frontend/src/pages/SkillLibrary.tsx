import { useState, useEffect } from "react";
import { getSkills, createSkill, deleteSkill, detectSkillPatterns } from "@/lib/api";
import CodeOutput from "@/components/CodeOutput";
import { BookOpen, Plus, Trash2, Search, Wand2, Loader2, Tag, Zap } from "lucide-react";

export default function SkillLibrary() {
  const [skills, setSkills] = useState<any[]>([]);
  const [category, setCategory] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [showDetect, setShowDetect] = useState(false);
  const [loading, setLoading] = useState(false);
  const [detectLoading, setDetectLoading] = useState(false);
  const [detectResult, setDetectResult] = useState<any>(null);
  const [error, setError] = useState("");

  // Create form
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newCategory, setNewCategory] = useState("general");
  const [newTemplate, setNewTemplate] = useState("");
  const [newTags, setNewTags] = useState("");

  // Detect form
  const [detectCode, setDetectCode] = useState("");

  useEffect(() => {
    loadSkills();
  }, [category]);

  const loadSkills = async () => {
    try {
      const res = await getSkills(category || undefined);
      setSkills(res);
    } catch {
      setSkills([]);
    }
  };

  const handleCreate = async () => {
    if (!newName.trim() || !newTemplate.trim()) return;
    setLoading(true);
    setError("");
    try {
      await createSkill({
        name: newName,
        description: newDesc,
        category: newCategory,
        template: newTemplate,
        tags: newTags.split(",").map((t) => t.trim()).filter(Boolean),
      });
      setShowCreate(false);
      setNewName(""); setNewDesc(""); setNewTemplate(""); setNewTags("");
      loadSkills();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this skill?")) return;
    try {
      await deleteSkill(id);
      loadSkills();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleDetect = async () => {
    if (!detectCode.trim()) return;
    setDetectLoading(true);
    setDetectResult(null);
    try {
      const res = await detectSkillPatterns(detectCode);
      setDetectResult(res);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setDetectLoading(false);
    }
  };

  const categories = ["general", "testing", "deployment", "review", "architecture"];

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-indigo-100 rounded-xl">
            <BookOpen className="h-6 w-6 text-indigo-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Skill Library</h1>
            <p className="text-slate-500">Reusable AI skill templates — save, browse, and auto-detect patterns</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowDetect(!showDetect)}
            className="flex items-center gap-1.5 px-3 py-2 bg-purple-100 text-purple-700 hover:bg-purple-200 rounded-lg text-sm font-medium transition"
          >
            <Wand2 className="h-4 w-4" /> Auto-Detect
          </button>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="flex items-center gap-1.5 px-3 py-2 bg-indigo-600 text-white hover:bg-indigo-700 rounded-lg text-sm font-medium transition"
          >
            <Plus className="h-4 w-4" /> New Skill
          </button>
        </div>
      </div>

      {/* Category Filter */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => setCategory("")}
          className={`px-3 py-1.5 rounded-full text-xs font-medium transition ${!category ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}
        >
          All
        </button>
        {categories.map((c) => (
          <button
            key={c}
            onClick={() => setCategory(c)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium capitalize transition ${category === c ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}
          >
            {c}
          </button>
        ))}
      </div>

      {/* Auto-Detect Panel */}
      {showDetect && (
        <div className="bg-purple-50 border border-purple-200 rounded-xl p-5 space-y-3">
          <h3 className="font-semibold text-purple-900">Auto-Detect Patterns</h3>
          <p className="text-sm text-purple-700">Paste code to detect reusable patterns and auto-suggest skills to save.</p>
          <textarea
            value={detectCode}
            onChange={(e) => setDetectCode(e.target.value)}
            placeholder="Paste code here to detect patterns..."
            className="w-full h-32 p-3 border border-purple-200 rounded-lg text-sm font-mono"
          />
          <button
            onClick={handleDetect}
            disabled={detectLoading || !detectCode.trim()}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-slate-300 text-white rounded-lg text-sm font-medium"
          >
            {detectLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            Detect Patterns
          </button>
          {detectResult && (
            <div className="space-y-2 mt-3">
              {detectResult.suggested_skills?.map((s: any, i: number) => (
                <div key={i} className="bg-white p-3 rounded-lg border border-purple-100">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-sm">{s.name}</span>
                    <button
                      onClick={() => { setNewName(s.name); setNewDesc(s.description); setNewTemplate(s.template || ""); setNewCategory(s.category || "general"); setShowCreate(true); setShowDetect(false); }}
                      className="text-xs px-2 py-1 bg-indigo-100 text-indigo-700 rounded hover:bg-indigo-200"
                    >
                      Save as Skill
                    </button>
                  </div>
                  <p className="text-xs text-slate-600 mt-1">{s.description}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Create Panel */}
      {showCreate && (
        <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
          <h3 className="font-semibold text-slate-900">Create New Skill</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <input type="text" value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Skill Name *" className="p-2.5 border border-slate-300 rounded-lg text-sm" />
            <select value={newCategory} onChange={(e) => setNewCategory(e.target.value)} className="p-2.5 border border-slate-300 rounded-lg text-sm">
              {categories.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <input type="text" value={newDesc} onChange={(e) => setNewDesc(e.target.value)} placeholder="Description" className="w-full p-2.5 border border-slate-300 rounded-lg text-sm" />
          <textarea value={newTemplate} onChange={(e) => setNewTemplate(e.target.value)} placeholder="Skill Template / Content *" className="w-full h-32 p-3 border border-slate-300 rounded-lg text-sm font-mono" />
          <input type="text" value={newTags} onChange={(e) => setNewTags(e.target.value)} placeholder="Tags (comma separated)" className="w-full p-2.5 border border-slate-300 rounded-lg text-sm" />
          <div className="flex gap-2">
            <button onClick={handleCreate} disabled={loading} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white rounded-lg text-sm font-medium">
              {loading ? "Saving..." : "Save Skill"}
            </button>
            <button onClick={() => setShowCreate(false)} className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-sm">Cancel</button>
          </div>
        </div>
      )}

      {error && <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-sm">{error}</div>}

      {/* Skills Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {skills.length === 0 ? (
          <div className="col-span-2 text-center py-12 text-slate-400">
            <BookOpen className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p>No skills saved yet. Create one or use Auto-Detect to find patterns.</p>
          </div>
        ) : (
          skills.map((skill) => (
            <div key={skill.id} className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 hover:border-indigo-300 transition">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-slate-900">{skill.name}</h3>
                  <p className="text-xs text-slate-500 mt-0.5">{skill.description}</p>
                </div>
                <button onClick={() => handleDelete(skill.id)} className="p-1 text-slate-400 hover:text-red-500">
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span className="px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded text-[10px] font-medium capitalize">{skill.category}</span>
                <span className="text-[10px] text-slate-400 flex items-center gap-0.5">
                  <Zap className="h-3 w-3" /> {skill.usage_count} uses
                </span>
              </div>
              {skill.tags?.length > 0 && (
                <div className="flex gap-1 mt-2 flex-wrap">
                  {skill.tags.map((tag: string) => (
                    <span key={tag} className="px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded text-[10px] flex items-center gap-0.5">
                      <Tag className="h-2.5 w-2.5" />{tag}
                    </span>
                  ))}
                </div>
              )}
              {skill.template && (
                <div className="mt-3">
                  <CodeOutput code={skill.template} language="text" title="Template" maxHeight="120px" />
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
