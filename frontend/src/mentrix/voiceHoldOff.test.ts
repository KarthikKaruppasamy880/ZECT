import { describe, expect, it } from "vitest";
import { createVoiceHoldOff } from "./voiceHoldOff";

describe("voice Disconnect hold-off", () => {
  it("ignores wake after manual Disconnect until explicit Connect", () => {
    const h = createVoiceHoldOff();
    expect(h.shouldIgnoreWake()).toBe(false);
    h.onManualDisconnect();
    expect(h.isHoldOff()).toBe(true);
    expect(h.shouldIgnoreWake("wake")).toBe(true);
    expect(h.shouldIgnoreWake("connect")).toBe(false);
    h.onExplicitConnect();
    expect(h.shouldIgnoreWake("wake")).toBe(false);
  });
});
