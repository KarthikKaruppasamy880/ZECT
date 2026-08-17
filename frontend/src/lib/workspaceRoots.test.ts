import { describe, expect, it, beforeEach } from "vitest";
import {
  WORKSPACE_ROOTS_KEY,
  excludeWorkspaceRoot,
  includeWorkspaceRoot,
  excludedRootIds,
  visibleProjectRepos,
} from "./workspaceRoots";

const repos = [
  { repo_id: 1, project_id: 10, name: "zect" },
  { repo_id: 2, project_id: 10, name: "zoas" },
  { repo_id: 3, project_id: 10, name: "other" },
  { repo_id: 9, project_id: 11, name: "foreign" },
];

describe("workspaceRoots", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("defaults to every project repo as an authorized workspace root", () => {
    expect(excludedRootIds(10)).toEqual([]);
    expect(visibleProjectRepos(10, repos).map((r) => r.repo_id)).toEqual([1, 2, 3]);
  });

  it("remove from workspace excludes the root without dropping other projects", () => {
    excludeWorkspaceRoot(10, 2);
    expect(localStorage.getItem(WORKSPACE_ROOTS_KEY)).toContain("2");
    expect(visibleProjectRepos(10, repos).map((r) => r.repo_id)).toEqual([1, 3]);
    expect(visibleProjectRepos(11, repos).map((r) => r.repo_id)).toEqual([9]);
  });

  it("attach/include restores a previously removed root", () => {
    excludeWorkspaceRoot(10, 1);
    includeWorkspaceRoot(10, 1);
    expect(visibleProjectRepos(10, repos).map((r) => r.repo_id)).toEqual([1, 2, 3]);
  });
});
