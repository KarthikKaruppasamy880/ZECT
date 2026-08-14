/** Manual Disconnect hold-off: wake must not reconnect until explicit Connect. */

export type VoiceWakeSource = "wake" | "connect";

export function createVoiceHoldOff() {
  let holdOff = false;
  return {
    onManualDisconnect() {
      holdOff = true;
    },
    onExplicitConnect() {
      holdOff = false;
    },
    isHoldOff() {
      return holdOff;
    },
    shouldIgnoreWake(source: VoiceWakeSource = "wake") {
      return holdOff && source === "wake";
    },
  };
}
