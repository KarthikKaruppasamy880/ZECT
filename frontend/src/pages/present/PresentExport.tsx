import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { FileDown } from "lucide-react";
import PresentPhaseStrip from "@/pages/present/PresentPhaseStrip";
import { decodeDeckId, mentrixPresentPptxDownload, mentrixPresentQualityGate } from "@/lib/api";

export default function PresentExport() {
  const { deckId = "" } = useParams();
  const path = decodeDeckId(deckId);
  const [gate, setGate] = useState<{
    export_blocked: boolean;
    hard_blocked?: boolean;
    accept_warnings_allowed?: boolean;
    quality_passed: boolean;
    slide_count: number;
    overlap_count: number;
    clipped_text_count: number;
    covering_dump_count?: number;
    broken_rel_count?: number;
    hard_findings?: string[];
    warnings?: string[];
    final_quality_status?: string;
  } | null>(null);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [acceptWarnings, setAcceptWarnings] = useState(false);

  useEffect(() => {
    if (!path) return;
    mentrixPresentQualityGate(path)
      .then(setGate)
      .catch(() =>
        setGate({
          export_blocked: true,
          hard_blocked: true,
          quality_passed: false,
          slide_count: 0,
          overlap_count: 0,
          clipped_text_count: 0,
          hard_findings: ["quality_gate_unavailable"],
        }),
      );
  }, [path]);

  const hardBlocked = Boolean(gate?.export_blocked || gate?.hard_blocked);
  const warnings = gate?.warnings || [];
  const canAcceptWarnings = Boolean(gate?.accept_warnings_allowed) && !hardBlocked && warnings.length > 0;
  const blocked = hardBlocked || (canAcceptWarnings && !acceptWarnings);

  const exportPptx = async () => {
    if (!path || blocked || hardBlocked) return;
    setBusy(true);
    try {
      const { blob, filename } = await mentrixPresentPptxDownload(path);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename || "zect-deck.pptx";
      a.click();
      URL.revokeObjectURL(url);
      setStatus(`Exported ${blob.size} bytes`);
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Export failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4" data-testid="present-export">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-slate-900">Export / Present</h2>
        <PresentPhaseStrip deckId={deckId} current="export" />
      </div>
      {gate ? (
        <ul className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-800 space-y-1" data-testid="present-export-gate">
          <li>{gate.quality_passed ? "Quality passed" : `Quality ${gate.final_quality_status || "FAIL"}`}</li>
          <li>{gate.slide_count} slides</li>
          <li>{gate.overlap_count} collisions</li>
          <li>{gate.clipped_text_count} clipped / out of bounds</li>
          <li>{gate.covering_dump_count ?? 0} covering dumps</li>
          <li>{gate.broken_rel_count ?? 0} broken assets/rels</li>
          {gate.hard_findings?.length ? (
            <li className="text-rose-800" data-testid="present-export-hard-findings">
              Critical (cannot accept): {gate.hard_findings.join(", ")}
            </li>
          ) : null}
          {warnings.length ? <li>Warnings: {warnings.join(", ")}</li> : null}
          <li>Notes: {warnings.includes("notes_missing") ? "not ready" : "ready"}</li>
        </ul>
      ) : (
        <p className="text-xs text-slate-500">Checking export quality…</p>
      )}
      {hardBlocked ? (
        <p className="text-xs text-rose-800" data-testid="present-export-hard-block">
          Export is blocked until critical quality findings are repaired. Accepting warnings cannot override collisions,
          duplicate content, clipping, broken assets, or corrupt relationships.
        </p>
      ) : null}
      {canAcceptWarnings ? (
        <label className="flex items-center gap-2 text-xs text-amber-900" data-testid="present-export-accept-warnings">
          <input type="checkbox" checked={acceptWarnings} onChange={(e) => setAcceptWarnings(e.target.checked)} />
          Accept non-critical presentation-quality warnings and export
        </label>
      ) : null}
      <button
        type="button"
        data-testid="present-export-pptx"
        disabled={busy || !path || blocked}
        onClick={() => void exportPptx()}
        className="inline-flex items-center gap-1.5 rounded-lg bg-teal-800 px-3 py-2 text-xs text-white disabled:opacity-40"
      >
        <FileDown className="h-3.5 w-3.5" />
        Export PPTX
      </button>
      {status ? <p className="text-xs text-slate-600">{status}</p> : null}
    </div>
  );
}
