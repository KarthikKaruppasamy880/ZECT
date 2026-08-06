import { afterEach, describe, expect, it } from "vitest";
import { isAgentModeEnabled, setAgentModeEnabled } from "@/lib/featureFlags";

describe("agentMode feature flag", () => {
  afterEach(() => {
    setAgentModeEnabled(false);
  });

  it("toggles via localStorage", () => {
    setAgentModeEnabled(false);
    expect(isAgentModeEnabled()).toBe(false);
    setAgentModeEnabled(true);
    expect(isAgentModeEnabled()).toBe(true);
    setAgentModeEnabled(false);
    expect(isAgentModeEnabled()).toBe(false);
  });
});
