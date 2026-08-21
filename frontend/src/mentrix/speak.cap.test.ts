import { describe, expect, it } from "vitest";
import { PRESENT_SLIDE_SCRIPT_CAP, capPresentSlideScript } from "./speak";

describe("Present slide script cap", () => {
  it("does not use a 500-character meaning cap", () => {
    expect(PRESENT_SLIDE_SCRIPT_CAP).toBeGreaterThan(500);
    const long = "word ".repeat(400).trim();
    expect(capPresentSlideScript(long).endsWith("…")).toBe(false);
  });
});
