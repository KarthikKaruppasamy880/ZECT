import { describe, expect, it } from "vitest";
import { preferredPresentVoiceChoice } from "./presentVoiceChoice";

describe("preferredPresentVoiceChoice", () => {
  it("auto-selects clone when stored is empty or leftover stock Echo", () => {
    expect(preferredPresentVoiceChoice("", "v1", false)).toBe("clone:v1");
    expect(preferredPresentVoiceChoice("stock:echo", "v1", false)).toBe("clone:v1");
  });

  it("keeps stock Echo when the operator explicitly opted in", () => {
    expect(preferredPresentVoiceChoice("stock:echo", "v1", true)).toBe("stock:echo");
    expect(preferredPresentVoiceChoice("none", "v1", true)).toBe("none");
  });

  it("leaves an existing clone selection alone", () => {
    expect(preferredPresentVoiceChoice("clone:v2", "v1", false)).toBe("clone:v2");
  });
});
