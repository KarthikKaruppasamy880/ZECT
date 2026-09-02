import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

vi.mock("@/lib/api", () => ({
  getDocumentMarkdown: vi.fn(async () => ({ markdown: "" })),
  listWorkItemAttachments: vi.fn(async () => ({ attachments: [] })),
  linkAttachmentToWorkItem: vi.fn(async () => ({ ok: true })),
  uploadImageAttachment: vi.fn(),
  getAttachmentRawDataUrl: vi.fn(),
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

  it("restores the Context Used strip from the last persisted turn on mount, without a new ask", async () => {
    // The gap this closes: contextUsed only ever got set inside the live
    // ask() handler, so a reload/tab-switch showed the question/answer
    // history correctly but left the Context Used strip blank until the
    // user asked a brand-new question. Simulate history whose LAST turn
    // carries a persisted context_used summary distinct from developerAsk's
    // default mock, so a pass here can only be explained by history
    // restoration, not a live ask() call (which this test never triggers).
    vi.mocked(developerAskHistory).mockResolvedValueOnce({
      turns: [
        { question: "earlier question", answer: "earlier answer", model: "gpt-4o-mini", offline: false, created_at: null },
        {
          question: "latest question",
          answer: "latest answer",
          model: "gpt-4o-mini",
          offline: false,
          created_at: null,
          context_used: { knowledge: true, lattice_hits: 3, lattice_indexed: true, lattice_state: "READY", blueprint: true },
        },
      ],
    });

    render(<MentrixCodingAgentPanel workspaceRoot="C:/tmp/zect" workItemId={7} />);
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-tab"));

    await screen.findByTestId("mentrix-coding-agent-ask-history");
    const strip = await screen.findByTestId("mentrix-coding-agent-context-used");
    expect(strip).toHaveTextContent("Knowledge");
    expect(strip).toHaveTextContent("Blueprint");
    expect(strip).toHaveTextContent("3 hits");
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
