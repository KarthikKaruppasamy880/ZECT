import { describe, expect, it } from "vitest";
import { replaceSelectionInContent } from "@/components/WorkspaceInlinePanel";

describe("replaceSelectionInContent", () => {
  it("replaces a mid-file line range", () => {
    const src = "a\nb\nc\nd";
    const next = replaceSelectionInContent(
      src,
      { text: "b\nc", startLine: 2, endLine: 3, startColumn: 1, endColumn: 2 },
      "X\nY",
    );
    expect(next).toBe("a\nX\nY\nd");
  });
});
