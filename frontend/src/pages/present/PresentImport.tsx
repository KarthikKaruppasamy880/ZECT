import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Upload } from "lucide-react";
import { encodeDeckId, mentrixPresentImport } from "@/lib/api";
import { pickAllowlistedPptx } from "@/lib/pickLocalFile";

export default function PresentImport() {
  const nav = useNavigate();
  const [status, setStatus] = useState("");
  const isDesktop =
    typeof window !== "undefined" &&
    !!(window as Window & { zectDesktop?: { isDesktopApp?: boolean } }).zectDesktop?.isDesktopApp;

  const onImport = async (file: File | null) => {
    if (!file) return;
    setStatus("Importing…");
    try {
      const out = await mentrixPresentImport(file);
      nav(`/present/d/${encodeDeckId(out.path)}`);
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Import failed");
    }
  };

  const onDesktopBrowse = async () => {
    setStatus("Selecting…");
    try {
      const picked = await pickAllowlistedPptx();
      if (!picked) {
        setStatus("");
        return;
      }
      await onImport(picked.file);
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Import failed");
    }
  };

  return (
    <div className="space-y-3" data-testid="present-import-page">
      <h2 className="text-lg font-semibold text-slate-900">Import PPTX</h2>
      <p className="text-xs text-slate-600">Opens in Review / Edit. Not mixed into Create with AI.</p>
      <div className="flex flex-wrap gap-2">
        <label className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm cursor-pointer hover:border-teal-500">
          <Upload className="h-4 w-4" />
          Choose a .pptx file
          <input
            type="file"
            accept=".pptx,application/vnd.openxmlformats-officedocument.presentationml.presentation"
            className="hidden"
            data-testid="present-import-file"
            onChange={(e) => void onImport(e.target.files?.[0] || null)}
          />
        </label>
        {isDesktop ? (
          <button
            type="button"
            className="rounded-xl border border-teal-700 bg-teal-50 px-4 py-3 text-sm text-teal-900"
            data-testid="present-import-desktop-browse"
            onClick={() => void onDesktopBrowse()}
          >
            Browse (Desktop)
          </button>
        ) : null}
      </div>
      {status ? <p className="text-xs text-slate-600">{status}</p> : null}
    </div>
  );
}
