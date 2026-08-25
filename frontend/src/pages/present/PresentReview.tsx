import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
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
    final_quality_status?: string;
    document_critic?: { final_quality_status?: string; document_overlap_count?: number };
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

  return (
    <div className="space-y-3" data-testid="present-review">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-slate-900">Quality review</h2>
        <PresentPhaseStrip deckId={deckId} current="quality" />
      </div>
      {gate ? (
        <p className="text-xs text-slate-600" data-testid="present-review-quality">
          Quality {gate.final_quality_status || (gate.quality_passed ? "PASS" : "FAIL")} · {gate.slide_count} slides ·{" "}
          {gate.overlap_count} collisions · {gate.clipped_text_count} clipped
          {gate.export_blocked ? " · export blocked until layout is repaired" : ""}
          {gate.document_critic?.final_quality_status
            ? ` · document critic ${gate.document_critic.final_quality_status}`
            : ""}
        </p>
      ) : null}
      <PresentEditor pptxPath={path} variant="review" />
    </div>
  );
}
