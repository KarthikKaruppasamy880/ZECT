import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import WorkspaceIdeMenu from "@/components/WorkspaceIdeMenu";

describe("WorkspaceIdeMenu", () => {
  it("exposes Add Folder and Remove Folder on File", () => {
    const onAddFolder = vi.fn();
    const onRemoveFolder = vi.fn();
    render(
      <WorkspaceIdeMenu
        canRemoveFolder
        canSave={false}
        onAddFolder={onAddFolder}
        onRemoveFolder={onRemoveFolder}
        onSave={vi.fn()}
        terminalOpen
        canRunApp={false}
        onCloseTerminal={vi.fn()}
        onShowTerminal={vi.fn()}
        onRunAppLocally={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByTestId("workspace-menu-file"));
    expect(screen.getByTestId("workspace-menu-file-dropdown")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("workspace-menu-add-folder"));
    expect(onAddFolder).toHaveBeenCalled();
    fireEvent.click(screen.getByTestId("workspace-menu-file"));
    fireEvent.click(screen.getByTestId("workspace-menu-remove-folder"));
    expect(onRemoveFolder).toHaveBeenCalled();
  });

  it("closes the terminal panel and offers run-app-locally from Terminal", () => {
    const onCloseTerminal = vi.fn();
    const onShowTerminal = vi.fn();
    const onRunAppLocally = vi.fn();
    render(
      <WorkspaceIdeMenu
        canRemoveFolder
        canSave={false}
        terminalOpen
        canRunApp
        onAddFolder={vi.fn()}
        onRemoveFolder={vi.fn()}
        onSave={vi.fn()}
        onCloseTerminal={onCloseTerminal}
        onShowTerminal={onShowTerminal}
        onRunAppLocally={onRunAppLocally}
      />,
    );
    fireEvent.click(screen.getByTestId("workspace-menu-terminal"));
    fireEvent.click(screen.getByTestId("workspace-menu-close-terminal"));
    expect(onCloseTerminal).toHaveBeenCalled();
    fireEvent.click(screen.getByTestId("workspace-menu-terminal"));
    fireEvent.click(screen.getByTestId("workspace-menu-run-app"));
    expect(onRunAppLocally).toHaveBeenCalled();
  });
});
