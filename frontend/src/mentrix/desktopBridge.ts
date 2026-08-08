/**
 * Apply Mentrix Computer Mode tool results via Electron IPC.
 */
export type DesktopApplyResult = {
  ok: boolean;
  error?: string;
  skipped?: boolean;
  verified?: boolean;
  verification?: unknown;
  hint?: string;
};

function parseToolPayload(output: string | Record<string, unknown>): Record<string, unknown> | null {
  if (typeof output === "object" && output !== null) return output;
  try {
    return JSON.parse(output) as Record<string, unknown>;
  } catch {
    return null;
  }
}

/** Flatten nested companion tool payloads (args / electron_args). */
export function flattenDesktopArgs(parsed: Record<string, unknown>): Record<string, unknown> {
  const nested =
    (parsed.args && typeof parsed.args === "object" ? (parsed.args as Record<string, unknown>) : null) ||
    {};
  const electronArgs =
    (parsed.electron_args && typeof parsed.electron_args === "object"
      ? (parsed.electron_args as Record<string, unknown>)
      : null) || {};
  const out: Record<string, unknown> = {
    ...parsed,
    ...nested,
    ...electronArgs,
  };
  // Prefer nested text/coords when top-level missing
  for (const key of ["text", "x", "y", "app", "path", "file", "direction", "content", "filename", "folder"]) {
    if (out[key] == null && nested[key] != null) out[key] = nested[key];
    if (out[key] == null && electronArgs[key] != null) out[key] = electronArgs[key];
  }
  return out;
}

function normalizeDesktopAction(action: string): string {
  const a = String(action || "");
  if (a.startsWith("computer_")) return a.replace(/^computer_/, "") || a;
  if (a === "desktop_screenshot") return "screenshot";
  if (a === "desktop_write_note") return "write_note";
  if (a === "desktop_read") return "read_path";
  if (a === "desktop_open_presentation") return "open_presentation";
  return a;
}

async function reportDesktopAudit(entry: Record<string, unknown>): Promise<void> {
  try {
    const { apiFetch } = await import("@/lib/api");
    await apiFetch("/api/audit/desktop", {
      method: "POST",
      body: JSON.stringify(entry),
    });
  } catch {
    /* best-effort — never block desktop action */
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

  const action = normalizeDesktopAction(String(parsed.desktop));
  const args = flattenDesktopArgs(parsed);
  try {
    const res = (await computer(action, args)) as {
      ok?: boolean;
      error?: string;
      verified?: boolean;
      verification?: unknown;
      hint?: string;
    };
    void reportDesktopAudit({
      action,
      ok: Boolean(res?.ok),
      error: res?.error,
      verified: res?.verified,
      app: args.app,
      verification: res?.verification,
    });
    if (res?.ok === false) {
      return {
        ok: false,
        error: String(res.error || "desktop_failed"),
        verified: Boolean(res.verified),
        verification: res.verification,
        hint: res.hint ? String(res.hint) : undefined,
      };
    }
    return {
      ok: true,
      verified: res?.verified,
      verification: res?.verification,
    };
  } catch (e) {
    const err = e instanceof Error ? e.message : "desktop_failed";
    void reportDesktopAudit({ action, ok: false, error: err });
    return { ok: false, error: err };
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
