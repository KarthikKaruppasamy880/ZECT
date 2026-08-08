/** Desktop bridge helpers — flatten nested companion desktop payloads. */
import { describe, expect, it } from "vitest";
import { flattenDesktopArgs } from "./desktopBridge";

describe("flattenDesktopArgs", () => {
  it("merges nested args and electron_args", () => {
    const out = flattenDesktopArgs({
      desktop: "computer_type",
      args: { text: "hello", x: 1 },
      electron_args: { path: "C:\\\\note.md" },
      app: "notepad.exe",
    });
    expect(out.text).toBe("hello");
    expect(out.x).toBe(1);
    expect(out.path).toBe("C:\\\\note.md");
    expect(out.app).toBe("notepad.exe");
    expect(out.desktop).toBe("computer_type");
  });
});
