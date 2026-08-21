import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

vi.mock("@/lib/api", () => ({
  askQuestion: vi.fn(async () => ({ answer: "No edits.", model: "gpt-4o-mini", tokens_used: 1 })),
  generatePlan: vi.fn(),
  codingAgentSavePlan: vi.fn(),
  codingAgentListPlans: vi.fn(async () => ({ ok: true, plans: [] })),
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
import { askQuestion, codingAgentCreateSession } from "@/lib/api";

describe("Developer ASK mode", () => {
  it("asks without creating a coding session (zero edits)", async () => {
    render(<MentrixCodingAgentPanel workspaceRoot="C:/tmp/zect" />);
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-tab"));
    fireEvent.change(screen.getByTestId("mentrix-coding-agent-ask-input"), {
      target: { value: "What does main.py do?" },
    });
    fireEvent.click(screen.getByTestId("mentrix-coding-agent-ask-send"));
    await waitFor(() => expect(askQuestion).toHaveBeenCalled());
    expect(codingAgentCreateSession).not.toHaveBeenCalled();
    expect(await screen.findByTestId("mentrix-coding-agent-ask-answer")).toHaveTextContent("No edits.");
  });
});
