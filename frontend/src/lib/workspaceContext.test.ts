import { describe, expect, it } from "vitest";
import { contextPageFor, deriveProjectKey } from "./workspaceContext";

describe("contextPageFor", () => {
  it("scopes a base page by project key", () => {
    expect(contextPageFor("workspace", "acme-widgets")).toBe("workspace:acme-widgets");
    expect(contextPageFor("ask", "acme-widgets")).toBe("ask:acme-widgets");
    expect(contextPageFor("plan", "acme-widgets")).toBe("plan:acme-widgets");
  });

  it("falls back to the bare base page when there's no active project", () => {
    expect(contextPageFor("workspace", "")).toBe("workspace");
  });

  it("keeps two different projects' pages distinct", () => {
    const a = contextPageFor("workspace", deriveProjectKey("acme", "widgets"));
    const b = contextPageFor("workspace", deriveProjectKey("acme", "gadgets"));
    expect(a).not.toBe(b);
  });
});
