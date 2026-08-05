import { describe, expect, it } from "vitest";
import { isPathInsideRoot, languageFromPath, normalizePath } from "@/lib/workspacePaths";

describe("workspacePaths", () => {
  it("normalizes slashes", () => {
    expect(normalizePath("C:\\tmp\\repo\\")).toBe("C:/tmp/repo");
  });

  it("allows descendants only", () => {
    expect(isPathInsideRoot("/ws/a/b.ts", "/ws")).toBe(true);
    expect(isPathInsideRoot("/ws", "/ws")).toBe(true);
    expect(isPathInsideRoot("/other/a.ts", "/ws")).toBe(false);
    expect(isPathInsideRoot("/ws-evil/x", "/ws")).toBe(false);
  });

  it("maps languages", () => {
    expect(languageFromPath("a.tsx")).toBe("typescript");
    expect(languageFromPath("b.py")).toBe("python");
  });
});
