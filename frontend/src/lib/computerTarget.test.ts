import { describe, expect, it } from "vitest";
import { computerTargetHint, isMentrixForeground } from "./computerTarget";

describe("computerTargetHint", () => {
  it("explains mkdir still works when Electron is focused", () => {
    expect(isMentrixForeground("electron")).toBe(true);
    expect(computerTargetHint("electron", false)).toMatch(/folder create still works/i);
    expect(computerTargetHint("explorer.exe", true)).toBe("explorer.exe · allowlisted");
    expect(computerTargetHint("chrome.exe", false)).toBe("chrome.exe · not allowlisted");
  });
});
