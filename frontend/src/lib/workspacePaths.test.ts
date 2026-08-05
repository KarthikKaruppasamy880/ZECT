import { describe, expect, it } from "vitest";
import { isPathInsideRoot, languageFromPath, normalizePath, pathMatchesMarker } from "@/lib/workspacePaths";

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

  it("matches agent/git markers", () => {
    expect(pathMatchesMarker("/ws/src/a.ts", "/ws", ["src/a.ts"])).toBe(true);
    expect(pathMatchesMarker("/ws/src/a.ts", "/ws", ["/ws/src/a.ts"])).toBe(true);
    expect(pathMatchesMarker("/ws/src/a.ts", "/ws", ["other.ts"])).toBe(false);
  });
});
