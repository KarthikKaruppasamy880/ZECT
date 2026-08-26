import { Link, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import PresentEditor from "@/components/PresentEditor";
import PresentPhaseStrip from "@/pages/present/PresentPhaseStrip";
import { decodeDeckId, mentrixPresentQualityGate } from "@/lib/api";

export default function PresentReview() {
  const { deckId = "" } = useParams();
  const path = decodeDeckId(deckId);
  const [gate, setGate] = useState<{
    export_blocked: boolean;
    quality_passed: boolean;
    slide_count: number;
    overlap_count: number;
    clipped_text_count: number;
    rendered_overlap_count?: number;
    rendered_clipped_count?: number;
    template_conflict_count?: number;
    near_empty_slide_count?: number;
    final_quality_status?: string;
    hard_findings?: string[];
    quality_subchecks?: Record<string, string>;
  } | null>(null);

  useEffect(() => {
    if (!path) return;
    mentrixPresentQualityGate(path)
      .then(setGate)
      .catch(() => setGate(null));
  }, [path]);

  if (!path) {
    return <p className="text-sm text-rose-700">Missing deck path.</p>;
  }

  const verdict = gate?.final_quality_status || (gate?.quality_passed ? "PASS" : "FAIL");

  return (
    <div className="space-y-3 min-h-0 flex flex-col" data-testid="present-review">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-slate-900">Review deck</h2>
        <PresentPhaseStrip deckId={deckId} current="quality" />
      </div>
      {gate ? (
        <div
          className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-800 space-y-2"
          data-testid="present-review-quality"
        >
          <p className="font-medium">
            Quality: {verdict} · {gate.slide_count} slides · {gate.rendered_overlap_count ?? gate.overlap_count} rendered
            overlaps · {gate.rendered_clipped_count ?? gate.clipped_text_count} clipped
            {(gate.template_conflict_count ?? 0) > 0 ? ` · ${gate.template_conflict_count} template conflicts` : ""}
            {(gate.near_empty_slide_count ?? 0) > 0 ? ` · ${gate.near_empty_slide_count} near-empty` : ""}
          </p>
          {gate.export_blocked ? (
            <p className="text-xs text-amber-900">Export blocked until critical findings are repaired.</p>
          ) : null}
          {gate.hard_findings?.length ? (
            <p className="text-xs text-rose-800">Critical: {gate.hard_findings.join(", ")}</p>
          ) : null}
          <div className="flex flex-wrap gap-2 pt-1">
            <Link
              to={`/present/d/${deckId}/edit`}
              className="rounded-lg bg-teal-800 px-3 py-1.5 text-xs text-white"
              data-testid="present-review-edit"
            >
              Edit
            </Link>
            <Link
              to={`/present/d/${deckId}/rehearse`}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs text-slate-800"
              data-testid="present-review-rehearse"
            >
              Rehearse
            </Link>
            <Link
              to={`/present/d/${deckId}/export`}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs text-slate-800"
              data-testid="present-review-export"
            >
              Export
            </Link>
          </div>
        </div>
      ) : (
        <p className="text-xs text-slate-500">Loading quality summary…</p>
      )}
      <div className="min-h-[420px] flex-1">
        <PresentEditor pptxPath={path} variant="review" />
      </div>
    </div>
  );
}
