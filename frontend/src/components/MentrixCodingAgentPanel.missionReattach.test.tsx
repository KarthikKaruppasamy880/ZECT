/**
 * A Mission runs on the server, but the pane only ever held it in React
 * state. Navigating away and back -- or reloading -- showed an empty "start a
 * mission" form while the real Mission was still running, and the user had no
 * way back to it. That is finding F4 / section 1 items 9 and 11 of
 * ZECT_CMS_REAL_PROJECT_CODING_AGENT_GOLDEN_BENCHMARK_V1.md.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

const codingAgentGetMission = vi.fn();

vi.mock("@/lib/api", () => ({
  developerAsk: vi.fn(async () => ({ answer: "a", work_item_id: 1 })),
  developerAskHistory: vi.fn(async () => ({ turns: [] })),
  developerPlan: vi.fn(),
  codingAgentGetMission: (...args: unknown[]) => codingAgentGetMission(...args),
  codingAgentGetPlan: vi.fn(async () => {
    throw new Error("plan_not_found");
  }),
  codingAgentSavePlan: vi.fn(),
  codingAgentListPlans: vi.fn(async () => ({ ok: true, plans: [] })),
  codingAgentCreateMission: vi.fn(),
  codingAgentApprovePlan: vi.fn(),
  codingAgentResolveMentions: vi.fn(),
  codingAgentCreateSession: vi.fn(),
  codingAgentGetSession: vi.fn(),
  codingAgentStream: vi.fn(),
  codingAgentApproveGit: vi.fn(),
  codingAgentCancelMission: vi.fn(),
  codingAgentResumeMission: vi.fn(),
  codingAgentRetryMission: vi.fn(),
  codingAgentCancel: vi.fn(),
  codingAgentApprove: vi.fn(),
  mentrixStartRun: vi.fn(),
}));

vi.mock("@/components/ModelSelector", () => ({
  default: () => <div data-testid="model-selector" />,
}));

import MentrixCodingAgentPanel from "./MentrixCodingAgentPanel";

const RUNNING = {
  id: "mission-abc",
  phase: "awaiting_git_approval",
  status: "running",
  files: ["src/a.ts", "src/b.ts"],
};

describe("Mission re-attachment (F4)", () => {
  beforeEach(() => {
    codingAgentGetMission.mockReset();
  });

  it("re-attaches to the mission id it is handed instead of showing an empty form", async () => {
    codingAgentGetMission.mockResolvedValue(RUNNING);
    render(<MentrixCodingAgentPanel workspaceRoot="C:/repo" missionId="mission-abc" />);

    await waitFor(() => expect(codingAgentGetMission).toHaveBeenCalledWith("mission-abc"));
    await waitFor(() =>
      expect(screen.getByTestId("mentrix-coding-agent-phase")).toHaveTextContent("awaiting_git_approval"),
    );
    expect(screen.getByTestId("mentrix-coding-agent-status")).toHaveTextContent("running");
  });

  it("republishes the re-attached mission's files so the Explorer shows them", async () => {
    codingAgentGetMission.mockResolvedValue(RUNNING);
    const onFilesChanged = vi.fn();
    render(
      <MentrixCodingAgentPanel workspaceRoot="C:/repo" missionId="mission-abc" onFilesChanged={onFilesChanged} />,
    );

    await waitFor(() => expect(onFilesChanged).toHaveBeenCalledWith(["src/a.ts", "src/b.ts"]));
  });

  it("reports the mission id upward so the page can persist it", async () => {
    codingAgentGetMission.mockResolvedValue(RUNNING);
    const onMissionChanged = vi.fn();
    render(
      <MentrixCodingAgentPanel workspaceRoot="C:/repo" missionId="mission-abc" onMissionChanged={onMissionChanged} />,
    );

    await waitFor(() => expect(onMissionChanged).toHaveBeenCalledWith("mission-abc"));
  });

  it("does not re-fetch a mission it already holds", async () => {
    codingAgentGetMission.mockResolvedValue(RUNNING);
    const { rerender } = render(<MentrixCodingAgentPanel workspaceRoot="C:/repo" missionId="mission-abc" />);
    await waitFor(() => expect(codingAgentGetMission).toHaveBeenCalledTimes(1));

    rerender(<MentrixCodingAgentPanel workspaceRoot="C:/repo" missionId="mission-abc" />);
    await waitFor(() => expect(codingAgentGetMission).toHaveBeenCalledTimes(1));
  });

  it("leaves the start form usable when the mission id is stale", async () => {
    codingAgentGetMission.mockRejectedValue(new Error("mission_not_found"));
    render(<MentrixCodingAgentPanel workspaceRoot="C:/repo" missionId="gone" />);

    await waitFor(() => expect(codingAgentGetMission).toHaveBeenCalled());
    await waitFor(() =>
      expect(screen.queryByTestId("mentrix-coding-agent-mission-reattaching")).not.toBeInTheDocument(),
    );
    expect(screen.getByTestId("mentrix-coding-agent-mission-goal")).not.toBeDisabled();
  });

  it("never fetches when there is no mission id", async () => {
    render(<MentrixCodingAgentPanel workspaceRoot="C:/repo" />);
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-plan-tab"));
    expect(codingAgentGetMission).not.toHaveBeenCalled();
  });
});

describe("Context Used reports the canonical Lattice state (F6)", () => {
  beforeEach(() => {
    codingAgentGetMission.mockReset();
  });

  const withContext = (context_used: Record<string, unknown>) => {
    codingAgentGetMission.mockResolvedValue({ ...RUNNING, files: [], context_used });
    render(<MentrixCodingAgentPanel workspaceRoot="C:/repo" missionId="mission-abc" />);
    return screen.findByTestId("mentrix-coding-agent-context-used");
  };

  it("shows READY with the hit count", async () => {
    const strip = await withContext({ lattice_state: "READY", lattice_indexed: true, lattice_hits: 12 });
    expect(strip).toHaveTextContent("Lattice READY · 12 hits");
  });

  it("does not claim NOT_INDEXED for a repository the Lattice is still indexing", async () => {
    const strip = await withContext({ lattice_state: "INDEXING", lattice_indexed: false });
    expect(strip).toHaveTextContent("Lattice INDEXING");
    expect(strip).not.toHaveTextContent("NOT_INDEXED");
  });

  it("distinguishes STALE from never indexed", async () => {
    const strip = await withContext({ lattice_state: "STALE", lattice_indexed: false });
    expect(strip).toHaveTextContent("Lattice STALE");
  });

  it("falls back to the boolean for a context pack persisted before lattice_state existed", async () => {
    const strip = await withContext({ lattice_indexed: true, lattice_hits: 3 });
    expect(strip).toHaveTextContent("Lattice READY · 3 hits");
  });
});
