import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

vi.mock("@/lib/api", () => ({
  developerAsk: vi.fn(async () => ({
    work_item_id: 42,
    answer: "fresh answer",
    project_intelligence: { lattice: { status: "READY", hits: [] }, knowledge: [], blueprint: {} },
  })),
  developerAskHistory: vi.fn(async () => ({
    turns: [
      { question: "earlier question", answer: "earlier answer", model: "gpt-4o-mini", offline: false, created_at: null },
    ],
  })),
  developerPlan: vi.fn(),
  codingAgentSavePlan: vi.fn(),
  codingAgentListPlans: vi.fn(async () => ({ ok: true, plans: [] })),
  codingAgentGetPlan: vi.fn(async () => {
    throw new Error("plan_not_found");
  }),
  codingAgentCreateMission: vi.fn(),
  codingAgentCreateSession: vi.fn(),
  codingAgentApprovePlan: vi.fn(),
  codingAgentApproveGit: vi.fn(),
  codingAgentCancelMission: vi.fn(),
  codingAgentResumeMission: vi.fn(),
  codingAgentRetryMission: vi.fn(),
  codingAgentCancel: vi.fn(),
  codingAgentApprove: vi.fn(),
  codingAgentStream: vi.fn(),
  mentrixStartRun: vi.fn(),
}));

vi.mock("@/components/ModelSelector", () => ({
  default: () => <div data-testid="model-selector" />,
}));

import MentrixCodingAgentPanel from "./MentrixCodingAgentPanel";
import { developerAsk, developerAskHistory } from "@/lib/api";

describe("Ask conversation persistence (V2 closure §5)", () => {
  it("restores prior turns on mount when a work item id is already known", async () => {
    render(<MentrixCodingAgentPanel workspaceRoot="C:/tmp/zect" workItemId={7} />);
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-tab"));

    await waitFor(() => expect(developerAskHistory).toHaveBeenCalledWith(7));
    expect(await screen.findByTestId("mentrix-coding-agent-ask-history")).toHaveTextContent("earlier question");
    expect(screen.getByTestId("mentrix-coding-agent-ask-history")).toHaveTextContent("earlier answer");
  });

  it("lifts the resolved work_item_id to the parent so the next Ask reuses it", async () => {
    const onWorkItemResolved = vi.fn();
    render(
      <MentrixCodingAgentPanel workspaceRoot="C:/tmp/zect" onWorkItemResolved={onWorkItemResolved} />,
    );
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-tab"));
    fireEvent.change(screen.getByTestId("mentrix-coding-agent-ask-input"), {
      target: { value: "first question" },
    });
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-send"));

    await waitFor(() => expect(developerAsk).toHaveBeenCalled());
    await waitFor(() => expect(onWorkItemResolved).toHaveBeenCalledWith(42));
  });

  it("appends new turns to the transcript instead of replacing the prior answer", async () => {
    render(<MentrixCodingAgentPanel workspaceRoot="C:/tmp/zect" workItemId={7} />);
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-tab"));
    await screen.findByTestId("mentrix-coding-agent-ask-history");

    fireEvent.change(screen.getByTestId("mentrix-coding-agent-ask-input"), {
      target: { value: "new question" },
    });
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-send"));

    await waitFor(() => expect(developerAsk).toHaveBeenCalled());
    const history = await screen.findByTestId("mentrix-coding-agent-ask-history");
    expect(history).toHaveTextContent("earlier question");
    expect(history).toHaveTextContent("fresh answer");
  });
});
