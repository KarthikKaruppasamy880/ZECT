/** HUD copy for Computer Mode foreground — Electron is never an allowlisted click/type target. */

export function isMentrixForeground(processName: string): boolean {
  const name = (processName || "").toLowerCase();
  return name.includes("electron") || name.includes("zect");
}

export function computerTargetHint(processName: string, allowlisted: boolean): string {
  const name = (processName || "unknown").trim() || "unknown";
  if (isMentrixForeground(name) && !allowlisted) {
    return `${name} · Mentrix is in front — folder create still works; click/type needs Explorer/Notepad focused`;
  }
  return `${name}${allowlisted ? " · allowlisted" : " · not allowlisted"}`;
}
