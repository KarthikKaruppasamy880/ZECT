import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createProject } from "@/lib/api";
import { ArrowLeft } from "lucide-react";

export default function CreateProject() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [team, setTeam] = useState("");
  const [repoOwner, setRepoOwner] = useState("");
  const [repoName, setRepoName] = useState("");
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    try {
      const repos =
        repoOwner.trim() && repoName.trim()
          ? [{ owner: repoOwner.trim(), repo_name: repoName.trim(), default_branch: "main" }]
          : [];
      const project = await createProject({
        name: name.trim(),
        description: description.trim(),
        team: team.trim(),
        current_stage: "ask",
        repos,
      } as Parameters<typeof createProject>[0]);
      navigate(`/projects/${project.id}`);
    } catch {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-2xl">
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-4"
      >
        <ArrowLeft className="h-4 w-4" /> Back
      </button>

      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h1 className="text-xl font-bold text-slate-900 mb-1">Create New Project</h1>
        <p className="text-sm text-slate-500 mb-6">Set up a new engineering project in ZECT</p>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Project Name *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              placeholder="e.g. Policy Admin Modernization"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              placeholder="Brief description of the project"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Team</label>
            <input
              type="text"
              value={team}
              onChange={(e) => setTeam(e.target.value)}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              placeholder="e.g. Platform Engineering"
            />
          </div>

          <div className="border-t border-slate-100 pt-5">
            <p className="text-sm font-medium text-slate-700 mb-3">Link GitHub Repository (optional)</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-500 mb-1">Owner</label>
                <input
                  type="text"
                  value={repoOwner}
                  onChange={(e) => setRepoOwner(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="e.g. KarthikKaruppasamy880"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">Repository</label>
                <input
                  type="text"
                  value={repoName}
                  onChange={(e) => setRepoName(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="e.g. ZECT"
                />
              </div>
            </div>
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="submit"
              disabled={saving || !name.trim()}
              className="bg-indigo-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50"
            >
              {saving ? "Creating..." : "Create Project"}
            </button>
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="border border-slate-200 text-slate-600 px-6 py-2 rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
