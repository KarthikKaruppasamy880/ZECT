/**
 * Fetch Skills + Dream lesson context for Mentrix turns (silent no-op on failure).
 */
import { apiFetch } from "@/lib/api";

export async function fetchMentrixAgentContext(opts: {
  skillId?: string;
  projectId?: string;
}): Promise<string> {
  try {
    const params = new URLSearchParams();
    if (opts.skillId) params.set("skill_id", opts.skillId);
    if (opts.projectId) params.set("project_id", opts.projectId);
    const qs = params.toString();
    const res = await apiFetch(`/api/mentrix/companion/agent-context${qs ? `?${qs}` : ""}`);
    if (!res.ok) return "";
    const data = (await res.json()) as { text?: string; ok?: boolean };
    return (data.text || "").trim();
  } catch {
    return "";
  }
}
