import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

vi.mock("@/lib/api", () => ({
  codingAgentStreamMission: vi.fn(async () => {}),
  getDocumentMarkdown: vi.fn(async () => ({ markdown: "" })),
  listWorkItemAttachments: vi.fn(async () => ({ attachments: [] })),
  linkAttachmentToWorkItem: vi.fn(async () => ({ ok: true })),
  uploadImageAttachment: vi.fn(),
  getAttachmentRawDataUrl: vi.fn(),
  developerAsk: vi.fn(async () => ({
    work_item_id: 1,
    answer: "No edits.",
    project_intelligence: { lattice: { status: "READY", hits: [{ id: "a" }] }, knowledge: [], blueprint: {} },
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
import { codingAgentCreateSession, developerAsk } from "@/lib/api";

describe("Developer ASK mode", () => {
  it("shows Implement vs Ship/PR labels without cloning an IDE menubar", () => {
    render(<MentrixCodingAgentPanel workspaceRoot="C:/tmp/zect" />);
    expect(screen.getByTestId("mentrix-coding-agent-mission-tab")).toHaveTextContent(/Ship\/PR/i);
    expect(screen.getByTestId("mentrix-coding-agent-history-tab")).toHaveTextContent(/Implement/i);
    expect(screen.queryByRole("menuitem", { name: /Go to File/i })).toBeNull();
  });

  it("asks without creating a coding session (zero edits)", async () => {
    render(<MentrixCodingAgentPanel workspaceRoot="C:/tmp/zect" />);
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-tab"));
    fireEvent.change(screen.getByTestId("mentrix-coding-agent-ask-input"), {
      target: { value: "What does main.py do?" },
    });
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-send"));
    await waitFor(() => expect(developerAsk).toHaveBeenCalled());
    expect(codingAgentCreateSession).not.toHaveBeenCalled();
    expect(await screen.findByTestId("mentrix-coding-agent-ask-answer")).toHaveTextContent("No edits.");
  });

  it("sends repository_id, repository_ids and project_id instead of a folder path", async () => {
    render(
      <MentrixCodingAgentPanel
        workspaceRoot="C:/tmp/zect"
        projectId={9}
        roots={[
          { id: 44, label: "zoas", path: "C:/tmp/zect" },
          { id: 45, label: "zaf", path: "C:/tmp/zaf" },
        ]}
      />,
    );
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-tab"));
    fireEvent.change(screen.getByTestId("mentrix-coding-agent-ask-input"), {
      target: { value: "Explain Lattice ingest" },
    });
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-send"));
    await waitFor(() => expect(developerAsk).toHaveBeenCalled());
    expect(developerAsk).toHaveBeenCalledWith({
      question: "Explain Lattice ingest",
      project_id: 9,
      work_item_id: undefined,
      repository_id: 44,
      repository_ids: [44, 45],
    });
  });

  it("sends the active repo as the primary repository_id, not roots[0] (CP-01)", async () => {
    render(
      <MentrixCodingAgentPanel
        workspaceRoot="C:/tmp/zect"
        projectId={9}
        activeRepoId={45}
        roots={[
          { id: 44, label: "zoas", path: "C:/tmp/zect" },
          { id: 45, label: "zaf", path: "C:/tmp/zaf" },
        ]}
      />,
    );
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-tab"));
    fireEvent.change(screen.getByTestId("mentrix-coding-agent-ask-input"), {
      target: { value: "Explain Lattice ingest" },
    });
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-send"));
    await waitFor(() => expect(developerAsk).toHaveBeenCalled());
    expect(developerAsk).toHaveBeenCalledWith({
      question: "Explain Lattice ingest",
      project_id: 9,
      work_item_id: undefined,
      repository_id: 45,
      repository_ids: [44, 45],
    });
  });
});
