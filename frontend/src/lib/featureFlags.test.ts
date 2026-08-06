import { afterEach, describe, expect, it } from "vitest";
import { isDemoModeEnabled, setDemoModeEnabled } from "@/lib/featureFlags";

describe("demoMode feature flag", () => {
  afterEach(() => {
    setDemoModeEnabled(false);
  });

  it("toggles via localStorage", () => {
    setDemoModeEnabled(false);
    expect(isDemoModeEnabled()).toBe(false);
    setDemoModeEnabled(true);
    expect(isDemoModeEnabled()).toBe(true);
    setDemoModeEnabled(false);
    expect(isDemoModeEnabled()).toBe(false);
  });
});
