import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

vi.mock("@/lib/api", () => ({
  developerAsk: vi.fn(async () => ({ work_item_id: 42, answer: "It computes a sum." })),
  buildGenerate: vi.fn(async () => ({ generated_code: "def test_add(): ...", explanation: "Generated tests." })),
  reviewAnalyze: vi.fn(async () => ({ findings: [] })),
  reviewFixPrompt: vi.fn(async () => ({ fixed_code: "fixed", changes_summary: "no findings" })),
}));

import WorkspaceInlinePanel from "./WorkspaceInlinePanel";
import { developerAsk } from "@/lib/api";

describe("WorkspaceInlinePanel Ask/Explain route through the same Mission Ask history", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("Ask calls developerAsk with the current work_item_id, not a separate endpoint", async () => {
    render(
      <WorkspaceInlinePanel
        filePath="src/calc.py"
        content="def add(a, b):\n    return a + b\n"
        selection={null}
        repoId={7}
        workItemId={99}
        projectId={3}
        onApplyCode={() => {}}
      />,
    );
    fireEvent.change(screen.getByTestId("workspace-inline-ask-input"), {
      target: { value: "What does this function do?" },
    });
    fireEvent.click(screen.getByTestId("workspace-inline-ask"));

    await waitFor(() => expect(developerAsk).toHaveBeenCalled());
    const call = (developerAsk as unknown as { mock: { calls: unknown[][] } }).mock.calls[0][0] as {
      work_item_id?: number;
      project_id?: number;
      question: string;
    };
    expect(call.work_item_id).toBe(99);
    expect(call.project_id).toBe(3);
    expect(call.question).toContain("What does this function do?");
    expect(await screen.findByTestId("workspace-inline-answer")).toHaveTextContent("It computes a sum.");
  });

  it("Explain also calls developerAsk, folding in file context", async () => {
    render(
      <WorkspaceInlinePanel
        filePath="src/calc.py"
        content="def add(a, b):\n    return a + b\n"
        selection={null}
        repoId={7}
        workItemId={99}
        onApplyCode={() => {}}
      />,
    );
    fireEvent.click(screen.getByTestId("workspace-inline-explain"));

    await waitFor(() => expect(developerAsk).toHaveBeenCalled());
    const call = (developerAsk as unknown as { mock: { calls: unknown[][] } }).mock.calls[0][0] as {
      question: string;
    };
    expect(call.question).toContain("Explain this code clearly");
    expect(call.question).toContain("def add(a, b)");
  });

  it("a first call with no active WorkItem lifts the resolved id up", async () => {
    const onWorkItemResolved = vi.fn();
    render(
      <WorkspaceInlinePanel
        filePath="src/calc.py"
        content="x = 1"
        selection={null}
        repoId={7}
        workItemId={null}
        onApplyCode={() => {}}
        onWorkItemResolved={onWorkItemResolved}
      />,
    );
    fireEvent.click(screen.getByTestId("workspace-inline-ask"));
    await waitFor(() => expect(onWorkItemResolved).toHaveBeenCalledWith(42));
  });
});
