import { describe, expect, it } from "vitest";
import { deployPrefillFromActive, ultraReviewHref } from "./deployPrefill";

describe("deployPrefillFromActive", () => {
  it("prefills owner/repo and uses develop when that is checked out", () => {
    expect(
      deployPrefillFromActive({ owner: "zinnia", repo_name: "zoas", clone_branch: "develop" }, "develop"),
    ).toEqual({ owner: "zinnia", repo: "zoas", ref: "develop" });
  });

  it("keeps a non-develop checkout branch", () => {
    expect(
      deployPrefillFromActive({ owner: "zinnia", repo_name: "zoas", clone_branch: "feat/x" }, "feat/x"),
    ).toEqual({ owner: "zinnia", repo: "zoas", ref: "feat/x" });
  });

  it("defaults ref to develop when no branch is known", () => {
    expect(deployPrefillFromActive({ owner: "zinnia", repo_name: "zoas" })).toEqual({
      owner: "zinnia",
      repo: "zoas",
      ref: "develop",
    });
  });
});

describe("ultraReviewHref", () => {
  it("links Quality Ultra Review with active owner/repo", () => {
    expect(ultraReviewHref({ owner: "zinnia", repo_name: "zoas" })).toBe(
      "/code-review?owner=zinnia&repo=zoas",
    );
  });
});
