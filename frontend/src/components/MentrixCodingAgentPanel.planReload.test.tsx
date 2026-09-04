import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

const codingAgentGetPlan = vi.fn();
const developerPlan = vi.fn();
const codingAgentSavePlan = vi.fn(async (..._args: any[]) => ({
  ok: true,
  id: "1-coding",
  path: "C:/repo/.zect/plans/1-coding.plan.md",
  markdown: "body",
}));

vi.mock("@/lib/api", () => ({
  codingAgentStreamMission: vi.fn(async () => {}),
  getDocumentMarkdown: vi.fn(async () => ({ markdown: "" })),
  listWorkItemAttachments: vi.fn(async () => ({ attachments: [] })),
  linkAttachmentToWorkItem: vi.fn(async () => ({ ok: true })),
  uploadImageAttachment: vi.fn(),
  getAttachmentRawDataUrl: vi.fn(),
  developerAsk: vi.fn(async () => ({ answer: "a", work_item_id: 1 })),
  developerAskHistory: vi.fn(async () => ({ turns: [] })),
  developerPlan: (...args: any[]) => developerPlan(...args),
  codingAgentGetPlan: (...args: any[]) => codingAgentGetPlan(...args),
  codingAgentSavePlan: (...args: any[]) => codingAgentSavePlan(...args),
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

const openPlanTab = () => fireEvent.click(screen.getByTestId("mentrix-coding-agent-plan-tab"));

describe("PLAN draft survives leaving and re-entering the pane", () => {
  beforeEach(() => {
    codingAgentGetPlan.mockReset();
    codingAgentSavePlan.mockClear();
    developerPlan.mockReset();
  });

  it("opens the CP-05 grounded plan in Monaco automatically, without a manual Save Plan click", async () => {
    codingAgentGetPlan.mockRejectedValue(new Error("plan_not_found"));
    developerPlan.mockResolvedValue({
      work_item_id: 1,
      plan: "## Goal\n\nDo the thing.",
      repo_plan_path: "C:/repo/.zect/plans/1-coding.plan.md",
    });
    const onOpenPath = vi.fn();
    const onFilesChanged = vi.fn();
    render(
      <MentrixCodingAgentPanel
        workspaceRoot="C:/repo"
        workItemId={1}
        onOpenPath={onOpenPath}
        onFilesChanged={onFilesChanged}
      />,
    );
    openPlanTab();
    fireEvent.change(await screen.findByTestId("mentrix-coding-agent-plan-goal"), {
      target: { value: "Implement campaign creation" },
    });
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-revise-plan"));

    await waitFor(() => expect(developerPlan).toHaveBeenCalled());
    expect(onOpenPath).toHaveBeenCalledWith("C:/repo/.zect/plans/1-coding.plan.md");
    expect(onFilesChanged).toHaveBeenCalledWith(["C:/repo/.zect/plans/1-coding.plan.md"]);
    const pathButton = await screen.findByTestId("mentrix-coding-agent-plan-path");
    expect(pathButton).toHaveTextContent("1-coding.plan.md");
  });

  it("reloads the saved plan from the workspace on mount", async () => {
    codingAgentGetPlan.mockResolvedValue({
      ok: true,
      id: "1-coding",
      path: "C:/repo/.zect/plans/1-coding.plan.md",
      markdown: "## Saved plan\nfrom disk",
    });
    render(<MentrixCodingAgentPanel workspaceRoot="C:/repo" workItemId={1} />);
    openPlanTab();

    await waitFor(() =>
      expect(codingAgentGetPlan).toHaveBeenCalledWith("1-coding", "C:/repo"),
    );
    await waitFor(() =>
      expect((screen.getByTestId("mentrix-coding-agent-plan-md") as HTMLTextAreaElement).value).toContain(
        "from disk",
      ),
    );
  });

  it("shows the real plan file path and opens it in the editor when clicked", async () => {
    codingAgentGetPlan.mockResolvedValue({
      ok: true,
      id: "1-coding",
      path: "C:/repo/.zect/plans/1-coding.plan.md",
      markdown: "## Saved plan",
    });
    const onOpenPath = vi.fn();
    render(<MentrixCodingAgentPanel workspaceRoot="C:/repo" workItemId={1} onOpenPath={onOpenPath} />);
    openPlanTab();

    const pathButton = await screen.findByTestId("mentrix-coding-agent-plan-path");
    expect(pathButton).toHaveTextContent("1-coding.plan.md");
    fireEvent.click(pathButton);
    expect(onOpenPath).toHaveBeenCalledWith("C:/repo/.zect/plans/1-coding.plan.md");
  });

  it("does not clobber an in-progress draft with the older saved copy", async () => {
    let resolveGet: (v: unknown) => void = () => {};
    codingAgentGetPlan.mockReturnValue(new Promise((r) => (resolveGet = r)));
    render(<MentrixCodingAgentPanel workspaceRoot="C:/repo" workItemId={1} />);
    openPlanTab();

    fireEvent.change(screen.getByTestId("mentrix-coding-agent-plan-md"), {
      target: { value: "## My unsaved edit" },
    });
    resolveGet({ ok: true, id: "1-coding", path: "p", markdown: "## Stale from disk" });

    await waitFor(() =>
      expect((screen.getByTestId("mentrix-coding-agent-plan-md") as HTMLTextAreaElement).value).toBe(
        "## My unsaved edit",
      ),
    );
  });

  it("starts empty when the workspace has no saved plan yet", async () => {
    codingAgentGetPlan.mockRejectedValue(new Error("plan_not_found"));
    render(<MentrixCodingAgentPanel workspaceRoot="C:/repo" workItemId={1} />);
    openPlanTab();

    await waitFor(() => expect(codingAgentGetPlan).toHaveBeenCalled());
    expect((screen.getByTestId("mentrix-coding-agent-plan-md") as HTMLTextAreaElement).value).toBe("");
  });

  it("saves with the workspace so the plan lands in that repo", async () => {
    codingAgentGetPlan.mockRejectedValue(new Error("plan_not_found"));
    render(<MentrixCodingAgentPanel workspaceRoot="C:/repo" workItemId={1} />);
    openPlanTab();
    fireEvent.change(screen.getByTestId("mentrix-coding-agent-plan-md"), {
      target: { value: "## Plan" },
    });
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-save-plan"));

    await waitFor(() =>
      expect(codingAgentSavePlan).toHaveBeenCalledWith(
        expect.objectContaining({ work_item_or_run: "1", workspace: "C:/repo" }),
      ),
    );
  });
});
