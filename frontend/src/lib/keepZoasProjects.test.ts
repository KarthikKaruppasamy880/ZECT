import { describe, expect, it } from "vitest";
import { isZoasKeepProject, projectsToDeleteKeepingZoas } from "./keepZoasProjects";

describe("keep zoas project filter", () => {
  it("keeps zoas / zinnia/zoas / ZOAS Eval", () => {
    expect(isZoasKeepProject({ id: 1, name: "zoas" })).toBe(true);
    expect(isZoasKeepProject({ id: 2, name: "ZOAS Eval" })).toBe(true);
    expect(
      isZoasKeepProject({ id: 3, name: "other", repos: [{ owner: "zinnia", repo_name: "zoas" }] }),
    ).toBe(true);
  });

  it("never deletes the active zoas project and drops non-zoas rows", () => {
    const rows = [
      { id: 1, name: "zoas" },
      { id: 2, name: "scratch" },
      { id: 3, name: "demo" },
    ];
    const del = projectsToDeleteKeepingZoas(rows, 1);
    expect(del.map((p) => p.id)).toEqual([2, 3]);
  });
});
