import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
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
});
