import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

vi.mock("@/lib/api", () => ({
  listWorkItemAttachments: vi.fn(async () => ({ attachments: [] })),
  linkAttachmentToWorkItem: vi.fn(async () => ({ ok: true })),
  uploadImageAttachment: vi.fn(),
  getAttachmentRawDataUrl: vi.fn(),
  developerAsk: vi.fn(async () => ({
    work_item_id: 1,
    answer: "It's a screenshot of a dashboard.",
    project_intelligence: null,
  })),
  developerPlan: vi.fn(),
  codingAgentSavePlan: vi.fn(async () => ({ ok: true })),
  codingAgentListPlans: vi.fn(async () => ({ ok: true, plans: [] })),
  codingAgentGetPlan: vi.fn(async () => {
    throw new Error("plan_not_found");
  }),
  codingAgentCreateMission: vi.fn(async () => ({ id: "m-1", phase: "editing", files: [] })),
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
  uploadDocument: vi.fn(async () => ({ ok: true, artifact: { id: 501 } })),
  getDocumentMarkdown: vi.fn(async () => ({ markdown: "# Notes\n\nfrom the attached file" })),
}));

vi.mock("@/components/ModelSelector", () => ({
  default: () => <div data-testid="model-selector" />,
}));

import MentrixCodingAgentPanel from "./MentrixCodingAgentPanel";
import { codingAgentCreateMission, developerAsk, uploadDocument } from "@/lib/api";

function pngFile(name = "screenshot.png") {
  return new File(["fake-png-bytes"], name, { type: "image/png" });
}

function textFile(name = "notes.md") {
  return new File(["# Notes"], name, { type: "text/markdown" });
}

describe("Composer attachments", () => {
  it("ASK: pasting a screenshot attaches it and sends it as vision content", async () => {
    render(<MentrixCodingAgentPanel workspaceRoot="C:/tmp/zect" />);
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-tab"));

    const textarea = screen.getByTestId("mentrix-coding-agent-ask-input");
    fireEvent.change(textarea, { target: { value: "What is this a screenshot of?" } });

    const file = pngFile();
    fireEvent.paste(textarea, {
      clipboardData: {
        items: [{ kind: "file", type: "image/png", getAsFile: () => file }],
      },
    });

    await waitFor(() => expect(screen.getByTestId("mentrix-coding-agent-ask-image-chip")).toBeInTheDocument());

    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-send"));

    await waitFor(() => expect(developerAsk).toHaveBeenCalled());
    const call = (developerAsk as unknown as { mock: { calls: unknown[][] } }).mock.calls[0][0] as {
      images?: string[];
    };
    expect(call.images).toHaveLength(1);
    expect(call.images?.[0]).toMatch(/^data:image\/png;base64,/);
  });

  it("ASK: drag-and-dropping a text file attaches it via the document pipeline", async () => {
    render(<MentrixCodingAgentPanel workspaceRoot="C:/tmp/zect" />);
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-tab"));

    const dropzone = screen.getByTestId("mentrix-coding-agent-ask-dropzone");
    const file = textFile();
    fireEvent.drop(dropzone, { dataTransfer: { files: [file] } });

    await waitFor(() => expect(uploadDocument).toHaveBeenCalled());
    expect(await screen.findByTestId("mentrix-coding-agent-ask-attachment-chip")).toHaveTextContent("notes.md");
  });

  it("PLAN: attachment bar has image parity with ASK (not a reduced composer)", async () => {
    render(<MentrixCodingAgentPanel workspaceRoot="C:/tmp/zect" />);
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-plan-tab"));

    const input = screen.getByTestId("mentrix-coding-agent-plan-attach-input") as HTMLInputElement;
    expect(input.accept).toContain(".png");

    const file = textFile("design.md");
    fireEvent.change(input, { target: { files: [file] } });
    expect(await screen.findByTestId("mentrix-coding-agent-plan-attachment-chip")).toHaveTextContent("design.md");
  });

  it("PLAN: pasting a screenshot into the markdown editor attaches it", async () => {
    render(<MentrixCodingAgentPanel workspaceRoot="C:/tmp/zect" />);
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-plan-tab"));

    const md = screen.getByTestId("mentrix-coding-agent-plan-md");
    const file = pngFile();
    fireEvent.paste(md, { clipboardData: { items: [{ kind: "file", type: "image/png", getAsFile: () => file }] } });

    await waitFor(() => expect(screen.getByTestId("mentrix-coding-agent-plan-image-chip")).toBeInTheDocument());
  });

  it("MISSION: pasting a screenshot into the goal textarea attaches it", async () => {
    render(<MentrixCodingAgentPanel workspaceRoot="C:/tmp/zect" />);
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-mission-tab"));

    const goal = screen.getByTestId("mentrix-coding-agent-mission-goal");
    const file = pngFile();
    fireEvent.paste(goal, { clipboardData: { items: [{ kind: "file", type: "image/png", getAsFile: () => file }] } });

    await waitFor(() => expect(screen.getByTestId("mentrix-coding-agent-mission-image-chip")).toBeInTheDocument());
  });

  it("AGENT: attached document text is folded into the goal sent to codingAgentCreateMission", async () => {
    render(<MentrixCodingAgentPanel workspaceRoot="C:/tmp/zect" roots={[{ id: 1, label: "repo", path: "C:/tmp/zect" }]} />);
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-mission-tab"));

    const input = screen.getByTestId("mentrix-coding-agent-mission-attach-input") as HTMLInputElement;
    const file = textFile("spec.md");
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => expect(uploadDocument).toHaveBeenCalled());

    fireEvent.change(screen.getByTestId("mentrix-coding-agent-mission-goal"), {
      target: { value: "Implement the attached spec" },
    });
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-start-mission"));

    await waitFor(() => expect(codingAgentCreateMission).toHaveBeenCalled());
    const call = (codingAgentCreateMission as unknown as { mock: { calls: unknown[][] } }).mock.calls[0][0] as {
      goal: string;
    };
    expect(call.goal).toContain("Implement the attached spec");
    expect(call.goal).toContain("[attachment:spec.md]");
    expect(call.goal).toContain("from the attached file");
  });
});
