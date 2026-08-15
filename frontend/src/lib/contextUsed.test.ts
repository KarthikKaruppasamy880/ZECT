import { describe, it, expect } from "vitest";
import { buildContextUsedRows, canonicalLatticeState, latticeHeaderLabel } from "@/lib/contextUsed";

describe("buildContextUsedRows", () => {
  it("marks missing WorkItem and empty PI sources without inventing values", () => {
    const rows = buildContextUsedRows({ workItem: null, pi: null, model: null });
    const byId = Object.fromEntries(rows.map((r) => [r.id, r]));
    expect(byId.work_item.status).toBe("missing");
    expect(byId.repo.status).toBe("missing");
    expect(byId.lattice.status).toBe("missing");
    expect(byId.knowledge.status).toBe("not_used");
    expect(byId.memory.status).toBe("not_used");
    expect(byId.model.status).toBe("missing");
  });

  it("shows verified memory separately from unverified", () => {
    const rows = buildContextUsedRows({
      workItem: {
        id: 7,
        title: "Jira task",
        source: "jira",
        external_id: "ZECT-1",
        status: "INGESTED",
        repository_id: 3,
        repository_ref: "main",
        base_commit_sha: "abcdef012345",
      },
      pi: {
        lattice: { status: "ok" },
        blueprint: { snippet: "bp", freshness: "indexed" },
        knowledge: [{ content: "kb truth", verification_state: "curated" }],
        memory: [
          { content: "learned", verification_state: "unverified" },
          { content: "trusted", verification_state: "verified" },
        ],
        related_work: [{ id: 1, title: "prior", status: "DONE" }],
        skill_selection: [{ name: "mentrix-smoke" }],
        playbook_selection: [{ name: "ship" }],
        freshness: { knowledge: "present", memory: "present" },
      },
      model: {
        model: "local-model",
        local_configured: true,
        cloud_configured: false,
        route: { provider: "local", blocked: false, fallback_used: false },
      },
    });
    const byId = Object.fromEntries(rows.map((r) => [r.id, r]));
    expect(byId.work_item.status).toBe("used");
    expect(byId.work_item.detail).toContain("jira");
    expect(byId.repo.status).toBe("used");
    expect(byId.memory.status).toBe("used");
    expect(byId.memory.detail).toMatch(/verified/i);
    expect(byId.skills.status).toBe("used");
    expect(byId.playbooks.status).toBe("used");
    expect(byId.model.detail).toContain("provider=local");
    expect(byId.lattice.status).toBe("used");
    expect(byId.lattice.detail).toContain("state=READY");
  });

  it("flags unverified-only memory as unverified not used", () => {
    const rows = buildContextUsedRows({
      pi: {
        memory: [{ content: "guess", verification_state: "unverified" }],
      },
    });
    const mem = rows.find((r) => r.id === "memory");
    expect(mem?.status).toBe("unverified");
  });

  it("canonicalizes Lattice states for header and Context Used", () => {
    const rows = buildContextUsedRows({
      pi: { lattice: { state: "NOT_INDEXED", action_label: "Index repository" } },
    });
    const lattice = rows.find((r) => r.id === "lattice");
    expect(lattice?.detail).toContain("state=NOT_INDEXED");
    expect(canonicalLatticeState("ok")).toBe("READY");
    expect(canonicalLatticeState("")).toBe("NOT_APPLICABLE");
    expect(latticeHeaderLabel("READY")).toBe("Lattice READY");
  });
});
