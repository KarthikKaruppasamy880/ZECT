/** Normalize P1 ProjectIntelligence / WorkItem / model-readiness into Context Used rows. */

export type ContextUsedStatus = "used" | "missing" | "stale" | "not_used" | "unverified";

export type ContextUsedRow = {
  id: string;
  label: string;
  status: ContextUsedStatus;
  detail: string;
};

export type WorkItemLite = {
  id?: number;
  title?: string;
  status?: string;
  source?: string;
  external_id?: string;
  repository_id?: number | null;
  repository_ref?: string;
  base_commit_sha?: string;
};

export type RepoContextLite = {
  repository_id?: number;
  label?: string;
  repository_ref?: string;
  base_commit_sha?: string;
  freshness?: string;
  authorized?: boolean;
};

export type ProjectIntelligenceLite = {
  lattice?: { status?: string; freshness?: string; hits?: unknown[] };
  blueprint?: { snippet?: string; freshness?: string };
  knowledge?: Array<{ content?: string; verification_state?: string }>;
  memory?: Array<{ content?: string; verification_state?: string; freshness?: string }>;
  related_work?: Array<{ id?: number; title?: string; status?: string }>;
  skill_selection?: Array<{ name?: string; reason?: string }>;
  playbook_selection?: Array<{ name?: string; reason?: string }>;
  freshness?: Record<string, string>;
  repositories?: RepoContextLite[];
  multi_repo?: boolean;
};

export type ModelReadinessLite = {
  local_configured?: boolean;
  cloud_configured?: boolean;
  model?: string;
  route?: {
    provider?: string;
    blocked?: boolean;
    fallback_used?: boolean;
    fallback_reason?: string;
  };
};

function trunc(s: string, n = 120): string {
  const t = s.replace(/\s+/g, " ").trim();
  return t.length > n ? `${t.slice(0, n - 1)}…` : t;
}

export function buildContextUsedRows(input: {
  workItem?: WorkItemLite | null;
  pi?: ProjectIntelligenceLite | null;
  model?: ModelReadinessLite | null;
  activeRepoLabel?: string;
  repoContexts?: RepoContextLite[];
}): ContextUsedRow[] {
  const { workItem, pi, model, activeRepoLabel, repoContexts } = input;
  const rows: ContextUsedRow[] = [];

  if (workItem?.id) {
    const src = workItem.source || "user";
    const ext = workItem.external_id ? ` · ${workItem.external_id}` : "";
    rows.push({
      id: "work_item",
      label: "WorkItem / source",
      status: "used",
      detail: `#${workItem.id} [${workItem.status || "?"}] ${src}${ext} — ${workItem.title || ""}`.trim(),
    });
  } else {
    rows.push({
      id: "work_item",
      label: "WorkItem / source",
      status: "missing",
      detail: "No active WorkItem (Jira/Camunda/user) bound to this workspace",
    });
  }

  const multiRepos = repoContexts?.length ? repoContexts : pi?.repositories;
  if (multiRepos && multiRepos.length > 1) {
    for (const r of multiRepos) {
      const sha = r.base_commit_sha || "";
      const fr = String(r.freshness || "unknown");
      const status: ContextUsedStatus =
        r.authorized === false
          ? "missing"
          : fr === "ready"
            ? "used"
            : fr === "stale" || !sha
              ? "stale"
              : "used";
      rows.push({
        id: `repo-${r.repository_id ?? r.label}`,
        label: `Repo · ${r.label || r.repository_id}`,
        status,
        detail: [
          r.repository_ref ? `ref=${r.repository_ref}` : "",
          sha ? `commit=${sha.slice(0, 12)}` : "commit=missing",
          fr ? `freshness=${fr}` : "",
        ]
          .filter(Boolean)
          .join(" · "),
      });
    }
  } else {
    const ref = workItem?.repository_ref || "";
    const sha = workItem?.base_commit_sha || "";
    const repoId = workItem?.repository_id;
    if (repoId || ref || sha || activeRepoLabel) {
      const parts = [
        activeRepoLabel || (repoId != null ? `repo_id=${repoId}` : ""),
        ref ? `ref=${ref}` : "",
        sha ? `commit=${sha.slice(0, 12)}` : "commit=missing",
      ].filter(Boolean);
      rows.push({
        id: "repo",
        label: "Repository + commit",
        status: sha ? "used" : "stale",
        detail: parts.join(" · ") || "Repository identity incomplete",
      });
    } else {
      rows.push({
        id: "repo",
        label: "Repository + commit",
        status: "missing",
        detail: "No repository_id / ref / base_commit_sha",
      });
    }
  }

  const lattice = pi?.lattice;
  const latticeStatus = String(lattice?.status || pi?.freshness?.lattice || "unavailable");
  if (latticeStatus === "ok" || latticeStatus === "present") {
    rows.push({
      id: "lattice",
      label: "Lattice",
      status: lattice?.freshness === "ephemeral" ? "stale" : "used",
      detail: trunc(`status=${latticeStatus}${lattice?.freshness ? ` · freshness=${lattice.freshness}` : ""}`),
    });
  } else {
    rows.push({
      id: "lattice",
      label: "Lattice",
      status: "missing",
      detail: `Not available (${latticeStatus})`,
    });
  }

  const bp = pi?.blueprint;
  const snippet = String(bp?.snippet || "").trim();
  if (snippet) {
    const fr = String(bp?.freshness || pi?.freshness?.blueprint || "unknown");
    rows.push({
      id: "blueprint",
      label: "Blueprint",
      status: fr === "unknown" || fr === "ephemeral" ? "stale" : "used",
      detail: trunc(`${fr} — ${snippet}`),
    });
  } else {
    rows.push({
      id: "blueprint",
      label: "Blueprint",
      status: "not_used",
      detail: "No blueprint snippet in Project Intelligence",
    });
  }

  const knowledge = pi?.knowledge || [];
  if (knowledge.length) {
    rows.push({
      id: "knowledge",
      label: "Knowledge",
      status: "used",
      detail: trunc(`${knowledge.length} hit(s) — ${knowledge[0]?.content || ""}`),
    });
  } else {
    rows.push({
      id: "knowledge",
      label: "Knowledge",
      status: "not_used",
      detail: "No Knowledge hits in snapshot",
    });
  }

  const memory = pi?.memory || [];
  const verified = memory.filter((m) => {
    const v = String(m.verification_state || "").toLowerCase();
    return v === "verified" || v === "curated";
  });
  if (verified.length) {
    rows.push({
      id: "memory",
      label: "Verified Memory",
      status: "used",
      detail: trunc(`${verified.length} verified — ${verified[0]?.content || ""}`),
    });
  } else if (memory.length) {
    rows.push({
      id: "memory",
      label: "Verified Memory",
      status: "unverified",
      detail: `${memory.length} memory hit(s) present but none verified/curated — not used as verified`,
    });
  } else {
    rows.push({
      id: "memory",
      label: "Verified Memory",
      status: "not_used",
      detail: "No Memory hits in snapshot",
    });
  }

  const related = pi?.related_work || [];
  if (related.length) {
    rows.push({
      id: "related",
      label: "Related work",
      status: "used",
      detail: trunc(related.map((r) => `#${r.id} ${r.title || ""} [${r.status || ""}]`).join("; ")),
    });
  } else {
    rows.push({
      id: "related",
      label: "Related work",
      status: "not_used",
      detail: "No related WorkItems in snapshot",
    });
  }

  const skills = pi?.skill_selection || [];
  if (skills.length) {
    rows.push({
      id: "skills",
      label: "Selected Skills",
      status: "used",
      detail: trunc(skills.map((s) => s.name || "?").join(", ")),
    });
  } else {
    rows.push({
      id: "skills",
      label: "Selected Skills",
      status: "not_used",
      detail: "No skills selected",
    });
  }

  const playbooks = pi?.playbook_selection || [];
  if (playbooks.length) {
    rows.push({
      id: "playbooks",
      label: "Selected Playbook",
      status: "used",
      detail: trunc(playbooks.map((p) => p.name || "?").join(", ")),
    });
  } else {
    rows.push({
      id: "playbooks",
      label: "Selected Playbook",
      status: "not_used",
      detail: "No playbook selected",
    });
  }

  const fresh = pi?.freshness;
  if (fresh && Object.keys(fresh).length) {
    rows.push({
      id: "freshness",
      label: "Freshness",
      status: Object.values(fresh).some((v) => v === "empty" || v === "unavailable" || v === "unknown")
        ? "stale"
        : "used",
      detail: trunc(Object.entries(fresh).map(([k, v]) => `${k}=${v}`).join(" · ")),
    });
  } else {
    rows.push({
      id: "freshness",
      label: "Freshness",
      status: "missing",
      detail: "Freshness map not returned",
    });
  }

  if (model?.route || model?.model) {
    const provider = model.route?.provider || "unknown";
    const fb = model.route?.fallback_used
      ? `fallback=${model.route.fallback_reason || "yes"}`
      : "fallback=none";
    const blocked = model.route?.blocked ? " · blocked" : "";
    rows.push({
      id: "model",
      label: "Model / provider",
      status: model.route?.blocked ? "stale" : "used",
      detail: trunc(
        `model=${model.model || "?"} · provider=${provider} · local=${Boolean(model.local_configured)} · cloud=${Boolean(model.cloud_configured)} · ${fb}${blocked}`,
      ),
    });
  } else {
    rows.push({
      id: "model",
      label: "Model / provider",
      status: "missing",
      detail: "Model readiness not available",
    });
  }

  return rows;
}
