import { describe, expect, it } from "vitest";
import { sessionCapsForTools } from "./companionSessionGrants";

describe("sessionCapsForTools", () => {
  it("first Allow for list_dir covers later reads via desktop:view", () => {
    const caps = sessionCapsForTools(["desktop_list_dir"]);
    expect(caps).toContain("desktop:view");
    expect(caps).toContain("filesystem:scan");
    expect(caps).toContain("desktop:control");
  });

  it("mkdir still requires filesystem:move (not silent wipe)", () => {
    const caps = sessionCapsForTools(["desktop_mkdir"]);
    expect(caps).toContain("filesystem:move");
    expect(caps).not.toContain("desktop:view");
  });
});
