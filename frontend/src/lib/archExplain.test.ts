import { describe, expect, it } from "vitest";
import { explainIdFromMermaidLabel } from "./archExplain";

describe("explainIdFromMermaidLabel", () => {
  it("maps client, lattice, control, and docs labels", () => {
    expect(explainIdFromMermaidLabel("React UI")).toBe("client");
    expect(explainIdFromMermaidLabel("Workspace / coding engine")).toBe("lattice");
    expect(explainIdFromMermaidLabel("Permissions + audit + emergency stop")).toBe("control");
    expect(explainIdFromMermaidLabel("Knowledge Base")).toBe("docs");
    expect(explainIdFromMermaidLabel("unrelated node")).toBeNull();
  });
});
