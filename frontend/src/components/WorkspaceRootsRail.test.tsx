import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import WorkspaceRootsRail from "@/components/WorkspaceRootsRail";

vi.mock("@/lib/api", () => ({
  getRepoIdentity: vi.fn(async (repoId: number) => {
    if (repoId === 2) {
      return { ok: true, repo_id: 2, cloned: false, root_state: "ROOT_UNAVAILABLE", error: "path_not_found", branch: "main" };
    }
    return {
      ok: true,
      repo_id: repoId,
      cloned: true,
      root_state: "READY",
      branch: "main",
      dirty: false,
      origin_url: "https://example.com/zect.git",
    };
  }),
  latticeStatus: vi.fn(async () => ({ indexed: true, state: "READY", project_key: "local-zect", has_blueprint: false })),
}));

const repos = [
  { repo_id: 1, project_id: 10, owner: "local", repo_name: "zect", local_path: "C:/tmp/zect", clone_branch: "main" },
  { repo_id: 2, project_id: 10, owner: "local", repo_name: "zoas", local_path: "C:/missing/zoas", clone_branch: "main" },
];

describe("WorkspaceRootsRail", () => {
  beforeEach(() => {
    localStorage.setItem("zect_token", "test");
  });

  it("lists roots, flags ROOT_UNAVAILABLE, and emits select/remove", async () => {
    const onSelectRoot = vi.fn();
    const onRemoveRoot = vi.fn();
    const onAddRoot = vi.fn();
    render(
      <WorkspaceRootsRail
        projectId={10}
        repos={repos}
        activeRepoId={1}
        onSelectRoot={onSelectRoot}
        onRemoveRoot={onRemoveRoot}
        onAddRoot={onAddRoot}
      />,
    );
    expect(screen.getByTestId("workspace-roots-rail")).toBeInTheDocument();
    expect(screen.getByTestId("workspace-root-1")).toHaveAttribute("data-active", "true");
    await waitFor(() => expect(screen.getByTestId("workspace-root-unavailable-2")).toHaveTextContent("ROOT_UNAVAILABLE"));
    fireEvent.click(screen.getByTestId("workspace-root-select-2"));
    expect(onSelectRoot).toHaveBeenCalledWith(2);
    fireEvent.click(screen.getByTestId("workspace-root-remove-1"));
    expect(onRemoveRoot).toHaveBeenCalledWith(1);
    fireEvent.click(screen.getByTestId("workspace-add-root"));
    expect(onAddRoot).toHaveBeenCalled();
  });
});
