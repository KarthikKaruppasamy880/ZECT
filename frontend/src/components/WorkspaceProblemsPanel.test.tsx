import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

const workspaceProblems = vi.fn();
vi.mock("@/lib/api", () => ({ workspaceProblems: (...args: unknown[]) => workspaceProblems(...args) }));

import WorkspaceProblemsPanel from "./WorkspaceProblemsPanel";

describe("WorkspaceProblemsPanel shows real lint/typecheck diagnostics, not a mock", () => {
  beforeEach(() => {
    workspaceProblems.mockReset();
  });

  it("fetches on mount and renders real findings with tool + file:line", async () => {
    workspaceProblems.mockResolvedValueOnce({
      ok: true,
      checked: ["eslint", "tsc"],
      problems: [
        {
          tool: "eslint",
          severity: "error",
          path: "src/x.ts",
          abs_path: "/repo/src/x.ts",
          line: 4,
          column: 7,
          message: "no-unused-vars x is unused",
          repo_id: 1,
        },
      ],
      skipped: [],
    });
    render(<WorkspaceProblemsPanel repoIds={[1]} onOpen={vi.fn()} />);

    await waitFor(() => expect(workspaceProblems).toHaveBeenCalledWith([1]));
    expect(await screen.findByText(/src\/x\.ts:4/)).toBeInTheDocument();
    expect(screen.getByText("no-unused-vars x is unused")).toBeInTheDocument();
    expect(screen.getByText("Checked: eslint, tsc")).toBeInTheDocument();
  });

  it("clicking a finding opens the file at its abs_path", async () => {
    workspaceProblems.mockResolvedValueOnce({
      ok: true,
      checked: ["ruff"],
      problems: [
        { tool: "ruff", severity: "error", path: "app.py", abs_path: "/repo/app.py", line: 3, message: "F401", repo_id: 2 },
      ],
      skipped: [],
    });
    const onOpen = vi.fn();
    render(<WorkspaceProblemsPanel repoIds={[2]} onOpen={onOpen} />);

    const item = await screen.findByTestId("workspace-problem-item");
    fireEvent.click(item);
    expect(onOpen).toHaveBeenCalledWith("/repo/app.py", 2);
  });

  it("shows 'No problems' when the check comes back clean", async () => {
    workspaceProblems.mockResolvedValueOnce({ ok: true, checked: ["eslint"], problems: [], skipped: [] });
    render(<WorkspaceProblemsPanel repoIds={[1]} onOpen={vi.fn()} />);

    expect(await screen.findByText("No problems")).toBeInTheDocument();
  });

  it("does not call the API when there are no repo roots yet", () => {
    render(<WorkspaceProblemsPanel repoIds={[]} onOpen={vi.fn()} />);
    expect(workspaceProblems).not.toHaveBeenCalled();
    expect(screen.getByText("No lint/typecheck tooling detected")).toBeInTheDocument();
  });
});
