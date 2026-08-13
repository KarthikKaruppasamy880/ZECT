/** Pick a local folder path for importing an already-cloned Git repo. */

export type FolderPickResult = { path: string; method: "electron" | "web" } | null;

declare global {
  interface Window {
    zectDesktop?: {
      isDesktopApp?: boolean;
      selectDirectory?: (opts?: {
        title?: string;
        defaultPath?: string;
      }) => Promise<{ ok: boolean; canceled?: boolean; path?: string; error?: string }>;
    };
  }
}

/**
 * Prefer Electron native folder dialog; fall back to File System Access API in Chromium.
 * Returns null if the user cancels or neither picker is available.
 */
export async function pickLocalFolder(opts?: {
  title?: string;
  defaultPath?: string;
}): Promise<FolderPickResult> {
  const title = opts?.title || "Select local Git repository folder";

  const desktop = typeof window !== "undefined" ? window.zectDesktop : undefined;
  if (desktop?.isDesktopApp && typeof desktop.selectDirectory === "function") {
    try {
      const res = await desktop.selectDirectory({
        title,
        defaultPath: opts?.defaultPath,
      });
      if (res?.ok && res.path) return { path: res.path, method: "electron" };
      return null;
    } catch {
      /* fall through */
    }
  }

  // Chromium File System Access API (Chrome/Edge). Does not work in all browsers.
  const w = typeof window !== "undefined" ? (window as Window & {
    showDirectoryPicker?: (o?: { id?: string; mode?: "read" }) => Promise<FileSystemDirectoryHandle>;
  }) : undefined;

  if (typeof w?.showDirectoryPicker === "function") {
    try {
      const handle = await w.showDirectoryPicker({ id: "zect-import-repo", mode: "read" });
      // Browser cannot reveal absolute path for security — use handle.name only as a hint.
      // Ask user to confirm via Electron or paste when absolute path is required.
      const anyHandle = handle as FileSystemDirectoryHandle & { path?: string };
      if (anyHandle.path) {
        return { path: anyHandle.path, method: "web" };
      }
      // No absolute path in browser — return null and let caller keep paste UX.
      // Signal via custom event detail in throw message for UI messaging.
      throw new Error(
        `Browser cannot expose the full path for “${handle.name}”. Use the Desktop app Browse button, or paste the full folder path (e.g. C:\\\\Users\\\\…\\\\Desktop\\\\${handle.name}).`,
      );
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") return null;
      throw e;
    }
  }

  return null;
}
