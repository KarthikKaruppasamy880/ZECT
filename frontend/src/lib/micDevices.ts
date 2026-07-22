/** Mentrix mic / headset device picker helpers. */

export const MENTRIX_MIC_STORAGE_KEY = "mentrix_mic_device_id";

export type MicDevice = {
  deviceId: string;
  label: string;
};

export function getStoredMicDeviceId(): string {
  try {
    return localStorage.getItem(MENTRIX_MIC_STORAGE_KEY) || "";
  } catch {
    return "";
  }
}

export function setStoredMicDeviceId(deviceId: string): void {
  try {
    if (deviceId) localStorage.setItem(MENTRIX_MIC_STORAGE_KEY, deviceId);
    else localStorage.removeItem(MENTRIX_MIC_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

/** Request mic permission once so enumerateDevices returns labels. */
export async function ensureMicPermission(): Promise<boolean> {
  if (!navigator.mediaDevices?.getUserMedia) return false;
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    stream.getTracks().forEach((t) => t.stop());
    return true;
  } catch {
    return false;
  }
}

export async function listMicDevices(): Promise<MicDevice[]> {
  if (!navigator.mediaDevices?.enumerateDevices) return [];
  const devices = await navigator.mediaDevices.enumerateDevices();
  return devices
    .filter((d) => d.kind === "audioinput")
    .map((d, i) => ({
      deviceId: d.deviceId,
      label: d.label || `Microphone ${i + 1}`,
    }));
}

export function audioConstraintsForDevice(deviceId?: string): MediaTrackConstraints | true {
  if (!deviceId) return true;
  return {
    deviceId: { ideal: deviceId },
    echoCancellation: true,
    noiseSuppression: true,
  };
}
