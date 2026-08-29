import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

// jsdom does not implement scrollIntoView; ChatPane calls it on every new
// line, which the History-tab test below triggers.
Element.prototype.scrollIntoView = vi.fn();

vi.mock("@/lib/api", () => ({
  developerAsk: vi.fn(),
  developerPlan: vi.fn(),
  codingAgentSavePlan: vi.fn(),
  codingAgentListPlans: vi.fn(async () => ({ ok: true, plans: [] })),
  codingAgentCreateMission: vi.fn(async () => ({
    id: "m-1",
    phase: "editing",
    status: "running",
    files: [],
    context_used: { knowledge: true, lattice_hits: 4, lattice_indexed: true, blueprint: false },
  })),
  codingAgentCreateSession: vi.fn(async () => ({ id: "s-1", status: "running", events: [] })),
  codingAgentGetSession: vi.fn(async () => ({
    id: "s-1",
    status: "completed",
    context_used: { knowledge: false, lattice_hits: 2, lattice_indexed: true, blueprint: true },
  })),
  codingAgentStream: vi.fn(async (_sessionId: string, opts: { onEvent: (ev: unknown) => void }) => {
    // Real streaming has network latency between session creation and the
    // first event; a synchronous call here would race React's commit of
    // setSessionId(res.id), leaving handleEvent reading a stale ref.
    await new Promise((resolve) => setTimeout(resolve, 0));
    opts.onEvent({ sequence_id: 1, event: "completed", message: "done" });
  }),
  codingAgentApprovePlan: vi.fn(),
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
import { codingAgentGetSession } from "@/lib/api";

describe("Context Used is visible in Agent and Implement, not just Ask/Plan", () => {
  it("AGENT tab shows Context Used from the mission response", async () => {
    render(
      <MentrixCodingAgentPanel workspaceRoot="C:/tmp/zect" roots={[{ id: 1, label: "repo", path: "C:/tmp/zect" }]} />,
    );
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-mission-tab"));
    fireEvent.change(screen.getByTestId("mentrix-coding-agent-mission-goal"), {
      target: { value: "Fix add()" },
    });
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-start-mission"));

    const strip = await screen.findByTestId("mentrix-coding-agent-context-used");
    expect(strip).toHaveTextContent("Lattice 4 hits");
    expect(strip).toHaveTextContent("Knowledge");
  });

  it("Implement (History) tab fetches and shows Context Used once the run completes", async () => {
    render(<MentrixCodingAgentPanel workspaceRoot="C:/tmp/zect" />);
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-history-tab"));
    fireEvent.change(screen.getByTestId("mentrix-coding-agent-input"), {
      target: { value: "Fix add()" },
    });
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-send"));

    await waitFor(() => expect(codingAgentGetSession).toHaveBeenCalled());
    await waitFor(() =>
      expect(screen.getByTestId("mentrix-coding-agent-context-used")).toHaveTextContent("Lattice 2 hits"),
    );
    expect(screen.getByTestId("mentrix-coding-agent-context-used")).toHaveTextContent("Blueprint");
  });
});
