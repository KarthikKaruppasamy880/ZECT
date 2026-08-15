import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Upload } from "lucide-react";
import { encodeDeckId, mentrixPresentImport } from "@/lib/api";

export default function PresentImport() {
  const nav = useNavigate();
  const [status, setStatus] = useState("");

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

  return (
    <div className="space-y-3" data-testid="present-import-page">
      <h2 className="text-lg font-semibold text-slate-900">Import PPTX</h2>
      <p className="text-xs text-slate-600">Opens in Review / Edit. Not mixed into Create with AI.</p>
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
      {status ? <p className="text-xs text-slate-600">{status}</p> : null}
    </div>
  );
}
