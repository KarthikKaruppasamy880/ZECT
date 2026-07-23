/**
 * Apply Mentrix Computer Mode tool results via Electron IPC.
 */
export type DesktopApplyResult = {
  ok: boolean;
  error?: string;
  skipped?: boolean;
};

function parseToolPayload(output: string | Record<string, unknown>): Record<string, unknown> | null {
  if (typeof output === "object" && output !== null) return output;
  try {
    return JSON.parse(output) as Record<string, unknown>;
  } catch {
    return null;
  }
}

export async function applyDesktopToolOutput(
  output: string | Record<string, unknown>,
  computerMode: boolean,
): Promise<DesktopApplyResult> {
  const parsed = parseToolPayload(output);
  if (!parsed?.desktop) return { ok: true, skipped: true };

  if (!computerMode) {
    return { ok: false, error: "computer_mode_off" };
  }

  const computer = window.zectDesktop?.mentrix?.computer;
  if (!computer) {
    return { ok: false, error: "not_desktop_app" };
  }

  const action = String(parsed.desktop);
  try {
    const res = (await computer(action, {
      ...parsed,
      app: parsed.app,
      path: parsed.path,
    })) as { ok?: boolean; error?: string };
    if (res?.ok === false) {
      return { ok: false, error: String(res.error || "desktop_failed") };
    }
    return { ok: true };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "desktop_failed" };
  }
}

export const COMPUTER_MODE_HINT =
  "Enable Computer Mode on the HUD, then Allow again.";

export function isOpenAiQuotaError(message: string): boolean {
  const m = (message || "").toLowerCase();
  return m.includes("quota") || m.includes("billing details");
}

export const OPENAI_QUOTA_STATUS =
  "OpenAI quota exceeded — add billing at platform.openai.com, then Retry Realtime";
