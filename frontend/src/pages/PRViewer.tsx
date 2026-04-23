import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getGitHubPull, getGitHubPullFiles } from "@/lib/api";
import type { GitHubPR, GitHubPRFile } from "@/types";
import DiffViewer from "@/components/DiffViewer";
import {
  ArrowLeft,
  GitPullRequest,
  ExternalLink,
  User,
  Calendar,
  GitBranch,
} from "lucide-react";

function relativeTime(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function PRViewer() {
  const { id, owner, repo, number } = useParams<{
    id: string;
    owner: string;
    repo: string;
    number: string;
  }>();
  const [pr, setPR] = useState<GitHubPR | null>(null);
  const [files, setFiles] = useState<GitHubPRFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!owner || !repo || !number) return;
    Promise.all([
      getGitHubPull(owner, repo, Number(number)),
      getGitHubPullFiles(owner, repo, Number(number)),
    ])
      .then(([p, f]) => {
        setPR(p);
        setFiles(f);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [owner, repo, number]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-800" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <p className="text-red-700 font-medium">Error loading PR</p>
        <p className="text-sm text-red-500 mt-1">{error}</p>
      </div>
    );
  }

  if (!pr) return null;

  return (
    <div>
      <Link
        to={`/projects/${id}`}
        className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-4"
      >
        <ArrowLeft className="h-4 w-4" /> Back to Project
      </Link>

      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
        <div className="flex items-start gap-3 mb-4">
          <GitPullRequest
            className={`h-6 w-6 shrink-0 mt-0.5 ${
              pr.state === "merged"
                ? "text-purple-500"
                : pr.state === "open"
                ? "text-green-500"
                : "text-red-500"
            }`}
          />
          <div className="flex-1">
            <h1 className="text-xl font-bold text-slate-900">
              #{pr.number} {pr.title}
            </h1>
            <div className="flex items-center gap-4 mt-2 text-sm text-slate-500">
              <span className="flex items-center gap-1">
                <User className="h-3.5 w-3.5" /> {pr.author}
              </span>
              <span className="flex items-center gap-1">
                <Calendar className="h-3.5 w-3.5" /> {relativeTime(pr.updated_at)}
              </span>
              <span className="flex items-center gap-1">
                <GitBranch className="h-3.5 w-3.5" /> {pr.head_branch} → {pr.base_branch}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span
              className={`text-xs font-medium px-2.5 py-1 rounded capitalize ${
                pr.state === "merged"
                  ? "bg-purple-100 text-purple-700"
                  : pr.state === "open"
                  ? "bg-green-100 text-green-700"
                  : "bg-red-100 text-red-700"
              }`}
            >
              {pr.state}
            </span>
            <a
              href={pr.html_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-700 px-2.5 py-1 border border-indigo-200 rounded"
            >
              GitHub <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>

        <div className="flex items-center gap-6 text-sm border-t border-slate-100 pt-4">
          <div>
            <span className="text-slate-500">Changed files:</span>{" "}
            <span className="font-medium text-slate-800">{pr.changed_files}</span>
          </div>
          <div>
            <span className="text-slate-500">Additions:</span>{" "}
            <span className="font-medium text-green-600">+{pr.additions}</span>
          </div>
          <div>
            <span className="text-slate-500">Deletions:</span>{" "}
            <span className="font-medium text-red-600">-{pr.deletions}</span>
          </div>
        </div>

        {pr.body && (
          <div className="mt-4 border-t border-slate-100 pt-4">
            <p className="text-xs font-semibold text-slate-500 uppercase mb-2">Description</p>
            <div className="text-sm text-slate-700 whitespace-pre-wrap">{pr.body}</div>
          </div>
        )}
      </div>

      <DiffViewer files={files} />
    </div>
  );
}
