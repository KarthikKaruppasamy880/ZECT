import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

const mission = (overrides: Record<string, unknown> = {}) => ({
  id: "m1",
  goal: "g",
  phase: "awaiting_git_approval",
  status: "awaiting_git_approval",
  plan: "## Plan",
  plan_approved: true,
  git_approved: false,
  repos: [],
  files: [],
  commands: [],
  tests: {},
  blockers: [],
  approvals: { plan: true, git: false },
  review: {},
  pr: {},
  ci: {},
  no_auto_merge: true,
  persistence: "durable_json",
  events: [],
  evidence: [],
  ...overrides,
});

const resolvedPack = {
  ok: true,
  pack: {
    work_item_id: null,
    token_budget: 8000,
    token_used: 42,
    items: [
      {
        source_type: "mention:file",
        source_id: "calc.py",
        content: "def add(a, b): return a + b",
        verification_state: "workspace_file",
        freshness: "current",
        retrieval_score: 0,
        token_count: 42,
        selection_reason: "user_mentioned",
      },
    ],
  },
};

vi.mock("@/lib/api", () => ({
  developerAsk: vi.fn(),
  developerPlan: vi.fn(),
  codingAgentSavePlan: vi.fn(async () => ({ ok: true })),
  codingAgentListPlans: vi.fn(async () => ({ ok: true, plans: [] })),
  codingAgentCreateMission: vi.fn(async (body: { plan: string }) =>
    mission({ id: "created", phase: "awaiting_plan_approval", files: [], plan: body.plan }),
  ),
  codingAgentApprovePlan: vi.fn(async () => mission()),
  codingAgentResolveMentions: vi.fn(async () => resolvedPack),
  uploadDocument: vi.fn(),
  getDocumentMarkdown: vi.fn(),
  codingAgentCreateSession: vi.fn(),
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
import { codingAgentCreateMission, codingAgentResolveMentions } from "@/lib/api";

describe("PLAN composer @mentions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows the autocomplete dropdown while typing an in-progress @mention", () => {
    render(
      <MentrixCodingAgentPanel
        workspaceRoot="C:/tmp/zect"
        roots={[{ id: 1, label: "app", path: "C:/tmp/zect" }]}
      />,
    );
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-plan-tab"));
    fireEvent.change(screen.getByTestId("mentrix-coding-agent-plan-md"), {
      target: { value: "check @fi" },
    });
    expect(screen.getByTestId("mention-autocomplete")).toBeTruthy();
    expect(screen.getByTestId("mention-option-file")).toBeTruthy();

    fireEvent.click(screen.getByTestId("mention-option-file"));
    expect((screen.getByTestId("mentrix-coding-agent-plan-md") as HTMLTextAreaElement).value).toBe(
      "check @file:",
    );
  });

  it("resolves @mentions and prepends real resolved context to what the mission actually receives", async () => {
    render(
      <MentrixCodingAgentPanel
        workspaceRoot="C:/tmp/zect"
        roots={[{ id: 1, label: "app", path: "C:/tmp/zect" }]}
      />,
    );
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-plan-tab"));
    fireEvent.change(screen.getByTestId("mentrix-coding-agent-plan-md"), {
      target: { value: "Fix add() -- see @file:calc.py" },
    });
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-approve-build"));

    await waitFor(() => expect(codingAgentResolveMentions).toHaveBeenCalled());
    await waitFor(() => expect(codingAgentCreateMission).toHaveBeenCalled());

    const call = (codingAgentCreateMission as unknown as { mock: { calls: Array<[{ plan: string }]> } })
      .mock.calls[0][0];
    expect(call.plan).toContain("## Resolved Context");
    expect(call.plan).toContain("def add(a, b): return a + b");
    expect(call.plan).toContain("Fix add() -- see @file:calc.py");
  });

  it("shows the resolved Context Used strip after Save Plan (still on the PLAN tab)", async () => {
    render(
      <MentrixCodingAgentPanel
        workspaceRoot="C:/tmp/zect"
        roots={[{ id: 1, label: "app", path: "C:/tmp/zect" }]}
      />,
    );
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-plan-tab"));
    fireEvent.change(screen.getByTestId("mentrix-coding-agent-plan-md"), {
      target: { value: "see @file:calc.py" },
    });
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-save-plan"));

    await waitFor(() => expect(codingAgentResolveMentions).toHaveBeenCalled());
    const strip = await screen.findByTestId("mention-context-strip");
    expect(strip).toHaveTextContent("mention:file:calc.py");
    expect(strip).not.toHaveTextContent("unresolved");
  });
});
