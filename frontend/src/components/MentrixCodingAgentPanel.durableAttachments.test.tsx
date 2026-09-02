/**
 * Every pane's useComposerAttachments() instance used to be fully isolated
 * and self-resetting: an ASK attachment survived only inside the one
 * ask_turn.question text it was flattened into, and nothing durable ever
 * told PLAN or AGENT "this WorkItem has attachments". That is finding /
 * acceptance item 2 -- native attachments must persist to the Mission and
 * remain available in PLAN and AGENT without re-upload.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

const listWorkItemAttachments = vi.fn(async (..._args: any[]) => ({ attachments: [] as unknown[] }));
const linkAttachmentToWorkItem = vi.fn(async (..._args: any[]) => ({ ok: true }));
const uploadDocument = vi.fn(async (..._args: any[]) => ({ ok: true, artifact: { id: 501, kind: "document" } }));
const uploadImageAttachment = vi.fn(async (..._args: any[]) => ({ ok: true, artifact: { id: 777, kind: "image" } }));
const getDocumentMarkdown = vi.fn(async (..._args: any[]) => ({ markdown: "# Requirement\n\nBudget must be validated." }));
const developerAsk = vi.fn(async (..._args: any[]) => ({ answer: "ok", work_item_id: 9, project_intelligence: null }));

vi.mock("@/lib/api", () => ({
  listWorkItemAttachments: (...args: any[]) => listWorkItemAttachments(...args),
  linkAttachmentToWorkItem: (...args: any[]) => linkAttachmentToWorkItem(...args),
  uploadDocument: (...args: any[]) => uploadDocument(...args),
  uploadImageAttachment: (...args: any[]) => uploadImageAttachment(...args),
  getAttachmentRawDataUrl: vi.fn(),
  getDocumentMarkdown: (...args: any[]) => getDocumentMarkdown(...args),
  developerAsk: (...args: any[]) => developerAsk(...args),
  developerAskHistory: vi.fn(async () => ({ turns: [] })),
  developerPlan: vi.fn(),
  codingAgentGetPlan: vi.fn(async () => {
    throw new Error("plan_not_found");
  }),
  codingAgentSavePlan: vi.fn(async () => ({ ok: true, path: "p" })),
  codingAgentListPlans: vi.fn(async () => ({ ok: true, plans: [] })),
  codingAgentCreateMission: vi.fn(async () => ({ id: "m-1", phase: "editing", files: [] })),
  codingAgentGetMission: vi.fn(),
  codingAgentApprovePlan: vi.fn(),
  codingAgentResolveMentions: vi.fn(async () => ({ pack: { items: [] } })),
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

import { useState } from "react";
import MentrixCodingAgentPanel from "./MentrixCodingAgentPanel";

/** MentrixCodingAgentPanel doesn't own workItemId itself -- the host page
 * does, lifting it via onWorkItemResolved. This stands in for that host so
 * a fresh WorkItem created mid-test flows back down as a real prop. */
function Harness(props: React.ComponentProps<typeof MentrixCodingAgentPanel>) {
  const [workItemId, setWorkItemId] = useState<number | null>(props.workItemId ?? null);
  return <MentrixCodingAgentPanel {...props} workItemId={workItemId} onWorkItemResolved={setWorkItemId} />;
}

const ATTACHED = [
  { id: 501, filename: "brd.md", kind: "document", mime_type: "text/markdown" },
  { id: 777, filename: "wireframe.png", kind: "image", mime_type: "image/png" },
];

describe("Attachments persist to the WorkItem and are visible everywhere", () => {
  beforeEach(() => {
    listWorkItemAttachments.mockReset();
    listWorkItemAttachments.mockResolvedValue({ attachments: [] });
    linkAttachmentToWorkItem.mockClear();
    uploadDocument.mockClear();
    getDocumentMarkdown.mockClear();
    developerAsk.mockClear();
  });

  it("shows nothing when the work item has no attachments yet", () => {
    render(<MentrixCodingAgentPanel workspaceRoot="C:/repo" workItemId={9} />);
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-tab"));
    expect(screen.queryByTestId("mentrix-coding-agent-workitem-attachments")).not.toBeInTheDocument();
  });

  it("ASK shows an attachment that was made in this same work item", async () => {
    listWorkItemAttachments.mockResolvedValue({ attachments: ATTACHED });
    render(<MentrixCodingAgentPanel workspaceRoot="C:/repo" workItemId={9} />);
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-tab"));

    const strip = await screen.findByTestId("mentrix-coding-agent-workitem-attachments");
    expect(strip).toHaveTextContent("brd.md");
    expect(strip).toHaveTextContent("wireframe.png");
  });

  it("PLAN shows the same attachment list as ASK, without re-upload", async () => {
    listWorkItemAttachments.mockResolvedValue({ attachments: ATTACHED });
    render(<MentrixCodingAgentPanel workspaceRoot="C:/repo" workItemId={9} />);
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-plan-tab"));

    expect(await screen.findByTestId("mentrix-coding-agent-workitem-attachments")).toHaveTextContent("brd.md");
    expect(uploadDocument).not.toHaveBeenCalled();
  });

  it("AGENT shows the same attachment list as ASK, without re-upload", async () => {
    listWorkItemAttachments.mockResolvedValue({ attachments: ATTACHED });
    render(<MentrixCodingAgentPanel workspaceRoot="C:/repo" workItemId={9} />);
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-mission-tab"));

    expect(await screen.findByTestId("mentrix-coding-agent-workitem-attachments")).toHaveTextContent("brd.md");
    expect(uploadDocument).not.toHaveBeenCalled();
  });

  it("uploads already linked when the work item is already known", async () => {
    render(<MentrixCodingAgentPanel workspaceRoot="C:/repo" workItemId={9} />);
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-tab"));

    const input = screen.getByTestId("mentrix-coding-agent-ask-attach-input") as HTMLInputElement;
    const file = new File(["# BRD"], "brd.md", { type: "text/markdown" });
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => expect(uploadDocument).toHaveBeenCalled());
    const call = uploadDocument.mock.calls[0][0] as { workItemId?: number };
    expect(call.workItemId).toBe(9);
    // Already linked at upload time -- no redundant round trip needed.
    expect(linkAttachmentToWorkItem).not.toHaveBeenCalled();
  });

  it("links a document retroactively once the work item becomes known (attached before the first turn)", async () => {
    render(<Harness workspaceRoot="C:/repo" />);
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-tab"));

    const input = screen.getByTestId("mentrix-coding-agent-ask-attach-input") as HTMLInputElement;
    const file = new File(["# BRD"], "brd.md", { type: "text/markdown" });
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => expect(uploadDocument).toHaveBeenCalled());
    expect(linkAttachmentToWorkItem).not.toHaveBeenCalled();

    fireEvent.change(screen.getByTestId("mentrix-coding-agent-ask-input"), { target: { value: "a question" } });
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-send"));

    await waitFor(() => expect(linkAttachmentToWorkItem).toHaveBeenCalledWith(501, 9));
  });

  it("AGENT folds a document attached earlier in ASK into the mission goal without re-uploading it", async () => {
    listWorkItemAttachments.mockResolvedValue({ attachments: [ATTACHED[0]] });
    render(
      <MentrixCodingAgentPanel
        workspaceRoot="C:/repo"
        workItemId={9}
        roots={[{ id: 1, label: "repo", path: "C:/repo" }]}
      />,
    );
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-mission-tab"));
    fireEvent.change(screen.getByTestId("mentrix-coding-agent-mission-goal"), {
      target: { value: "Implement the requirement" },
    });
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-start-mission"));

    await waitFor(() => expect(getDocumentMarkdown).toHaveBeenCalledWith(501));
    expect(uploadDocument).not.toHaveBeenCalled();
  });
});

describe("Vision-capability hint (best-effort, non-blocking)", () => {
  it("warns when a non-vision-looking model has an image attached", async () => {
    listWorkItemAttachments.mockResolvedValue({ attachments: [] });
    render(<MentrixCodingAgentPanel workspaceRoot="C:/repo" model="local-llama" />);
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-tab"));

    const textarea = screen.getByTestId("mentrix-coding-agent-ask-input");
    const file = new File(["png"], "s.png", { type: "image/png" });
    fireEvent.paste(textarea, { clipboardData: { items: [{ kind: "file", type: "image/png", getAsFile: () => file }] } });

    expect(await screen.findByTestId("mentrix-coding-agent-ask-vision-hint")).toHaveTextContent("local-llama");
  });

  it("shows no hint for a known vision-capable model", async () => {
    listWorkItemAttachments.mockResolvedValue({ attachments: [] });
    render(<MentrixCodingAgentPanel workspaceRoot="C:/repo" model="gpt-4o-mini" />);
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-tab"));

    const textarea = screen.getByTestId("mentrix-coding-agent-ask-input");
    const file = new File(["png"], "s.png", { type: "image/png" });
    fireEvent.paste(textarea, { clipboardData: { items: [{ kind: "file", type: "image/png", getAsFile: () => file }] } });

    await waitFor(() => expect(screen.getByTestId("mentrix-coding-agent-ask-image-chip")).toBeInTheDocument());
    expect(screen.queryByTestId("mentrix-coding-agent-ask-vision-hint")).not.toBeInTheDocument();
  });

  it("shows no hint before any image is attached", () => {
    render(<MentrixCodingAgentPanel workspaceRoot="C:/repo" model="local-llama" />);
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-tab"));
    expect(screen.queryByTestId("mentrix-coding-agent-ask-vision-hint")).not.toBeInTheDocument();
  });
});
