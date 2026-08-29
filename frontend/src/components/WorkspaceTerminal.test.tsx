import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import WorkspaceTerminal from "./WorkspaceTerminal";

vi.mock("@/lib/api", () => ({
  runnerOutput: vi.fn(),
  runnerStart: vi.fn(),
  runnerStop: vi.fn(),
  codingAgentRuntimeRecipes: vi.fn(async () => ({
    ok: true,
    default_id: "pkg-dev",
    recipes: [{ id: "pkg-dev", kind: "frontend", label: "npm run dev", command: "npm run dev", cwdRel: ".", confirmRequired: false }],
  })),
}));

const mountCounts: Record<string, number> = {};

vi.mock("./RealTerminal", async () => {
  const { useEffect } = await import("react");
  return {
    default: ({ workspaceRoot }: { workspaceRoot: string }) => {
      // Mount tracking must fire once per component *instance* (on mount),
      // not once per render -- a bare counter in the function body would
      // also increment on every re-render triggered by a tab switch.
      useEffect(() => {
        mountCounts[workspaceRoot] = (mountCounts[workspaceRoot] || 0) + 1;
      }, [workspaceRoot]);
      return <div data-testid="real-terminal-stub">{workspaceRoot}</div>;
    },
  };
});

describe("WorkspaceTerminal", () => {
  it("shows attach-root CTA and disables input when cwd is empty", () => {
    render(
      <MemoryRouter>
        <WorkspaceTerminal workspaceRoot="" />
      </MemoryRouter>,
    );
    expect(screen.getByTestId("workspace-terminal-no-root")).toBeTruthy();
    expect(screen.getByTestId("workspace-terminal-attach-root")).toHaveAttribute("href", "/projects");
    expect(screen.getByTestId("workspace-terminal-input")).toBeDisabled();
    expect(screen.queryByTestId("real-terminal-stub")).toBeNull();
  });

  it("renders a real terminal and enables App Runner controls when a workspace root is attached", () => {
    render(
      <MemoryRouter>
        <WorkspaceTerminal workspaceRoot="C:/tmp/zect" />
      </MemoryRouter>,
    );
    expect(screen.getByTestId("real-terminal-stub")).toHaveTextContent("C:/tmp/zect");
    expect(screen.getByTestId("workspace-terminal-cwd")).toHaveTextContent(/C:\/tmp\/zect/i);
    expect(screen.getByTestId("workspace-terminal-input")).not.toBeDisabled();
    expect(screen.getByTestId("workspace-terminal-start-app")).not.toBeDisabled();
    expect(screen.getByTestId("workspace-terminal-help")).toHaveTextContent(/App Runner tracks background services/i);
    expect(screen.getByTestId("workspace-terminal-app-runner")).toHaveAttribute("href", "/app-runner");
  });

  it("uses the first authorized root when workspaceRoot is empty", () => {
    render(
      <MemoryRouter>
        <WorkspaceTerminal
          workspaceRoot=""
          roots={[{ repoId: 1, rootPath: "C:/tmp/zoas", label: "local/zoas" }]}
        />
      </MemoryRouter>,
    );
    expect(screen.getByTestId("real-terminal-stub")).toHaveTextContent("C:/tmp/zoas");
    expect(screen.getByTestId("workspace-terminal-cwd")).toHaveTextContent(/C:\/tmp\/zoas/i);
  });

  it("closes the panel and a session from the header and tab X", () => {
    const onClosePanel = vi.fn();
    const onCloseSession = vi.fn();
    render(
      <MemoryRouter>
        <WorkspaceTerminal
          workspaceRoot="C:/tmp/zect"
          sessions={[{ id: "t1", repoId: 1, rootPath: "C:/tmp/zect", label: "local/zect" }]}
          activeSessionId="t1"
          onClosePanel={onClosePanel}
          onCloseSession={onCloseSession}
        />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByTestId("workspace-terminal-close-panel"));
    expect(onClosePanel).toHaveBeenCalled();
    fireEvent.click(screen.getByTestId("workspace-terminal-tab-close-1"));
    expect(onCloseSession).toHaveBeenCalledWith("t1");
  });

  it("keeps every session's RealTerminal mounted across tab switches (does not kill and respawn the shell)", () => {
    for (const k of Object.keys(mountCounts)) delete mountCounts[k];
    function Harness() {
      const [activeSessionId, setActiveSessionId] = useState("t1");
      return (
        <WorkspaceTerminal
          workspaceRoot="C:/tmp/zect"
          sessions={[
            { id: "t1", repoId: 1, rootPath: "C:/tmp/repo-one", label: "repo-one" },
            { id: "t2", repoId: 2, rootPath: "C:/tmp/repo-two", label: "repo-two" },
          ]}
          activeSessionId={activeSessionId}
          onSelectSession={setActiveSessionId}
        />
      );
    }
    render(
      <MemoryRouter>
        <Harness />
      </MemoryRouter>,
    );
    // Both sessions' terminals mount immediately (not just the active tab).
    const stubs = screen.getAllByTestId("real-terminal-stub");
    expect(stubs.map((n) => n.textContent).sort()).toEqual(["C:/tmp/repo-one", "C:/tmp/repo-two"]);
    expect(mountCounts["C:/tmp/repo-one"]).toBe(1);
    expect(mountCounts["C:/tmp/repo-two"]).toBe(1);

    // Switching tabs must not unmount/remount either terminal.
    fireEvent.click(screen.getByTestId("workspace-terminal-tab-2"));
    fireEvent.click(screen.getByTestId("workspace-terminal-tab-1"));
    fireEvent.click(screen.getByTestId("workspace-terminal-tab-2"));
    expect(mountCounts["C:/tmp/repo-one"]).toBe(1);
    expect(mountCounts["C:/tmp/repo-two"]).toBe(1);
    expect(screen.getAllByTestId("real-terminal-stub")).toHaveLength(2);
  });
});
