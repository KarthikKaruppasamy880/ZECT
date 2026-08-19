/** Pick a local file path (Electron native dialog). */

export type FilePickResult = { path: string; method: "electron" } | null;

type FileFilter = { name: string; extensions: string[] };

type SelectFileFn = (opts?: {
  title?: string;
  defaultPath?: string;
  filters?: FileFilter[];
}) => Promise<{ ok?: boolean; canceled?: boolean; path?: string; error?: string }>;

type ReadPresentationFn = (
  filePath: string,
) => Promise<{ ok?: boolean; name?: string; base64?: string; error?: string; path?: string }>;

function desktopApi(): {
  isDesktopApp?: boolean;
  selectFile?: SelectFileFn;
  readPresentationFile?: ReadPresentationFn;
} | undefined {
  if (typeof window === "undefined") return undefined;
  return (
    window as Window & {
      zectDesktop?: {
        isDesktopApp?: boolean;
        selectFile?: SelectFileFn;
        readPresentationFile?: ReadPresentationFn;
      };
    }
  ).zectDesktop;
}

export async function pickLocalFile(opts?: {
  title?: string;
  defaultPath?: string;
  filters?: FileFilter[];
}): Promise<FilePickResult> {
  const desktop = desktopApi();
  if (!desktop?.isDesktopApp || typeof desktop.selectFile !== "function") return null;
  try {
    const res = await desktop.selectFile({
      title: opts?.title || "Select file",
      defaultPath: opts?.defaultPath,
      filters: opts?.filters,
    });
    if (res?.ok && res.path) return { path: res.path, method: "electron" };
    return null;
  } catch {
    return null;
  }
}

export async function pickAllowlistedPptx(): Promise<{ path: string; file: File } | null> {
  const picked = await pickLocalFile({
    title: "Select PowerPoint (.pptx)",
    filters: [{ name: "PowerPoint", extensions: ["pptx"] }],
  });
  if (!picked?.path) return null;
  const desktop = desktopApi();
  if (typeof desktop?.readPresentationFile !== "function") {
    throw new Error("Desktop file read is unavailable. Use Choose a .pptx file.");
  }
  const res = await desktop.readPresentationFile(picked.path);
  if (!res?.ok || !res.base64) {
    throw new Error(res?.error || "Path must be under Desktop, Documents, or Downloads.");
  }
  const binary = atob(res.base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  const file = new File([bytes], res.name || "imported.pptx", {
    type: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  });
  return { path: res.path || picked.path, file };
}
