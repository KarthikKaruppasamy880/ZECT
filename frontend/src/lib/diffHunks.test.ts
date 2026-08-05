import { describe, expect, it } from "vitest";
import { applyHunks, parseUnifiedHunks, revertHunks } from "@/lib/diffHunks";

const UNIFIED = `--- a/x
+++ b/x
@@ -1,3 +1,4 @@
 line1
-old
+new
 line3
+extra
`;

describe("diffHunks", () => {
  it("parses unified hunks", () => {
    const hunks = parseUnifiedHunks(UNIFIED);
    expect(hunks).toHaveLength(1);
    expect(hunks[0].oldStart).toBe(1);
    expect(hunks[0].newStart).toBe(1);
    expect(hunks[0].lines.filter((l) => l.kind === "+")).toHaveLength(2);
    expect(hunks[0].lines.filter((l) => l.kind === "-")).toHaveLength(1);
  });

  it("applies and reverts a hunk", () => {
    const base = "line1\nold\nline3";
    const hunks = parseUnifiedHunks(UNIFIED);
    const next = applyHunks(base, hunks);
    expect(next).toBe("line1\nnew\nline3\nextra");
    const back = revertHunks(next, hunks);
    expect(back).toBe(base);
  });
});
