import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import WorkspaceTerminal from "./WorkspaceTerminal";

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
    expect(screen.getByTestId("workspace-terminal-input").getAttribute("placeholder") || "").toMatch(/No workspace root/i);
  });

  it("enables the command field when a workspace root is attached", () => {
    render(
      <MemoryRouter>
        <WorkspaceTerminal workspaceRoot="C:/tmp/zect" />
      </MemoryRouter>,
    );
    expect(screen.getByTestId("workspace-terminal-input")).not.toBeDisabled();
    expect(screen.getByTestId("workspace-terminal-cwd")).toHaveTextContent(/C:\/tmp\/zect/i);
    expect(screen.getByTestId("workspace-terminal-cwd")).toHaveTextContent(/locked root/i);
    expect(screen.getByTestId("workspace-terminal-start-app")).not.toBeDisabled();
    expect(screen.getByTestId("workspace-terminal-help")).toHaveTextContent(/This folder is the locked root/i);
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
    expect(screen.getByTestId("workspace-terminal-input")).not.toBeDisabled();
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
});
