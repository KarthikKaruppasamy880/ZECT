import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import WorkspaceEditorTabs from "@/components/WorkspaceEditorTabs";

const tabs = [
  { repoId: 1, path: "C:/tmp/zect/README.md" },
  { repoId: 1, path: "C:/tmp/zect/app.tsx" },
];

describe("WorkspaceEditorTabs", () => {
  it("renders open files and switches / closes them", () => {
    const onSelect = vi.fn();
    const onClose = vi.fn();
    render(
      <WorkspaceEditorTabs
        tabs={tabs}
        activePath={tabs[0].path}
        dirtyPaths={new Set([tabs[1].path])}
        onSelect={onSelect}
        onClose={onClose}
      />,
    );
    expect(screen.getByTestId("workspace-editor-tabs")).toBeInTheDocument();
    expect(screen.getByTestId("workspace-editor-tab-README.md")).toHaveAttribute("data-active", "true");
    fireEvent.click(screen.getByTestId("workspace-editor-tab-app.tsx"));
    expect(onSelect).toHaveBeenCalledWith(tabs[1]);
    fireEvent.click(screen.getByTestId("workspace-editor-tab-close-app.tsx"));
    expect(onClose).toHaveBeenCalledWith(tabs[1]);
  });
});
