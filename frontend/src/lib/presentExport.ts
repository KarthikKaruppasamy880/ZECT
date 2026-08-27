type DesktopExportBridge = {
  isDesktopApp?: boolean;
  savePresentationFile?: (opts: {
    defaultName?: string;
    dataBase64?: string;
  }) => Promise<{ ok: boolean; canceled?: boolean; path?: string; bytes?: number }>;
};

export function desktopExportBridge(): DesktopExportBridge | undefined {
  return (window as Window & { zectDesktop?: DesktopExportBridge }).zectDesktop;
}

export async function downloadPresentPptxBlob(
  blob: Blob,
  filename: string,
): Promise<{ ok: boolean; canceled?: boolean; path?: string; bytes?: number; message: string }> {
  const name = filename || "zect-deck.pptx";
  const desktop = desktopExportBridge();
  if (desktop?.isDesktopApp && desktop.savePresentationFile) {
    const buf = await blob.arrayBuffer();
    const dataBase64 = btoa(String.fromCharCode(...new Uint8Array(buf)));
    const saved = await desktop.savePresentationFile({ defaultName: name, dataBase64 });
    if (saved.canceled) {
      return { ok: false, canceled: true, message: "Export canceled" };
    }
    if (saved.ok && saved.path) {
      return {
        ok: true,
        path: saved.path,
        bytes: saved.bytes || blob.size,
        message: `Saved to ${saved.path} (${(saved.bytes || blob.size).toLocaleString()} bytes)`,
      };
    }
  }
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  URL.revokeObjectURL(url);
  return { ok: true, bytes: blob.size, message: `Exported ${name} (${blob.size.toLocaleString()} bytes)` };
}
