/**
 * Clicking "Create Plan" from ASK was a bare tab switch -- the question,
 * the answer, the resolved @mention evidence, and any attached requirement
 * document were all dropped, so the user had to re-paste everything into
 * PLAN. This closes section 1 item 4 of
 * ZECT_CMS_REAL_PROJECT_CODING_AGENT_GOLDEN_BENCHMARK_V1.md.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

const developerAsk = vi.fn(async () => ({
  answer: "Use the existing CampaignService.",
  work_item_id: 7,
  project_intelligence: {
    lattice: { status: "READY", hits: [{ a: 1 }, { b: 2 }] },
    knowledge: [{ content: "k" }],
    blueprint: { snippet: "" },
  },
}));
const developerAskHistory = vi.fn(async () => ({ turns: [] }));
const codingAgentResolveMentions = vi.fn(async () => ({
  pack: { items: [] },
}));

vi.mock("@/lib/api", () => ({
  developerAsk: (...args: unknown[]) => developerAsk(...args),
  developerAskHistory: (...args: unknown[]) => developerAskHistory(...args),
  developerPlan: vi.fn(),
  codingAgentGetPlan: vi.fn(async () => {
    throw new Error("plan_not_found");
  }),
  codingAgentSavePlan: vi.fn(),
  codingAgentListPlans: vi.fn(async () => ({ ok: true, plans: [] })),
  codingAgentCreateMission: vi.fn(),
  codingAgentGetMission: vi.fn(),
  codingAgentApprovePlan: vi.fn(),
  codingAgentResolveMentions: (...args: unknown[]) => codingAgentResolveMentions(...args),
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

const goToAsk = () => fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-tab"));
const goToPlan = () => fireEvent.click(screen.getByTestId("mentrix-coding-agent-plan-tab"));

const planMarkdown = () => (screen.getByTestId("mentrix-coding-agent-plan-md") as HTMLTextAreaElement).value;

describe("ASK to PLAN auto-seeding", () => {
  beforeEach(() => {
    developerAsk.mockClear();
  });

  it("carries the asked question and answer into the plan draft", async () => {
    render(<MentrixCodingAgentPanel workspaceRoot="C:/repo" workItemId={7} />);
    goToAsk();
    fireEvent.change(screen.getByTestId("mentrix-coding-agent-ask-input"), {
      target: { value: "How should campaign parameters be validated?" },
    });
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-send"));
    await waitFor(() => expect(developerAsk).toHaveBeenCalled());

    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-create-plan"));
    goToPlan();

    const md = planMarkdown();
    expect(md).toContain("How should campaign parameters be validated?");
    expect(md).toContain("Use the existing CampaignService.");
    expect((screen.getByTestId("mentrix-coding-agent-plan-goal") as HTMLInputElement).value).toBe(
      "How should campaign parameters be validated?",
    );
  });

  it("carries the resolved evidence and the attached requirement document", async () => {
    codingAgentResolveMentions.mockResolvedValue({
      pack: {
        items: [
          {
            source_type: "file",
            source_id: "campaign_service.py",
            content: "class CampaignService: ...",
            verification_state: "verified",
          },
        ],
      },
    });
    render(<MentrixCodingAgentPanel workspaceRoot="C:/repo" workItemId={7} />);
    goToAsk();
    fireEvent.change(screen.getByTestId("mentrix-coding-agent-ask-input"), {
      target: { value: "@file:campaign_service.py what does this do?" },
    });
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-send"));
    await waitFor(() => expect(developerAsk).toHaveBeenCalled());

    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-create-plan"));
    goToPlan();

    expect(planMarkdown()).toContain("class CampaignService");
  });

  it("carries the findings summary from the last Ask response", async () => {
    render(<MentrixCodingAgentPanel workspaceRoot="C:/repo" workItemId={7} />);
    goToAsk();
    fireEvent.change(screen.getByTestId("mentrix-coding-agent-ask-input"), { target: { value: "context?" } });
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-send"));
    await waitFor(() => expect(developerAsk).toHaveBeenCalled());

    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-create-plan"));
    goToPlan();

    expect(planMarkdown()).toContain("Lattice READY · 2 hits");
  });

  it("is a one-shot handoff: a later unrelated visit to PLAN is not reseeded", async () => {
    // PlanPane itself does not yet persist a draft across an unmount (that
    // is the separate workspace-local plan store slice) -- what this test
    // guards is narrower: the *same* ASK content must not reapply itself a
    // second time once it has already been delivered once.
    render(<MentrixCodingAgentPanel workspaceRoot="C:/repo" workItemId={7} />);
    goToAsk();
    fireEvent.change(screen.getByTestId("mentrix-coding-agent-ask-input"), { target: { value: "first question" } });
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-send"));
    await waitFor(() => expect(developerAsk).toHaveBeenCalled());
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-create-plan"));
    goToPlan();
    expect(planMarkdown()).toContain("first question");

    goToAsk();
    goToPlan();

    expect(planMarkdown()).not.toContain("first question");
  });

  it("leaves PLAN empty when the user never clicked Create Plan", () => {
    render(<MentrixCodingAgentPanel workspaceRoot="C:/repo" workItemId={7} />);
    goToPlan();
    expect(planMarkdown()).toBe("");
  });
});
