import { describe, expect, it, vi } from "vitest";
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
  files: ["calc.py"],
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

vi.mock("@/lib/api", () => ({
  developerAsk: vi.fn(),
  developerPlan: vi.fn(),
  codingAgentSavePlan: vi.fn(async () => ({ ok: true })),
  codingAgentListPlans: vi.fn(async () => ({ ok: true, plans: [] })),
  codingAgentCreateMission: vi.fn(async () =>
    mission({ id: "created", phase: "awaiting_plan_approval", files: [] }),
  ),
  codingAgentApprovePlan: vi.fn(async () => mission()),
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
import { codingAgentApprovePlan } from "@/lib/api";

describe("PLAN -> Approve & Build refreshes the real Explorer/Diff", () => {
  it("calls onFilesChanged with the approved mission's files, not just on manual actions", async () => {
    const onFilesChanged = vi.fn();
    render(
      <MentrixCodingAgentPanel
        workspaceRoot="C:/tmp/zect"
        onFilesChanged={onFilesChanged}
        roots={[{ id: 1, label: "app", path: "C:/tmp/zect" }]}
      />,
    );

    fireEvent.click(screen.getByTestId("mentrix-coding-agent-plan-tab"));
    fireEvent.change(screen.getByTestId("mentrix-coding-agent-plan-md"), {
      target: { value: "## Fix add()" },
    });
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-approve-build"));

    await waitFor(() => expect(codingAgentApprovePlan).toHaveBeenCalledWith("created"));
    await waitFor(() => expect(onFilesChanged).toHaveBeenCalledWith(["calc.py"]));
  });
});
