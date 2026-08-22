import { Link, useParams } from "react-router-dom";
import PresentEditor from "@/components/PresentEditor";
import { decodeDeckId } from "@/lib/api";

export default function PresentStudio() {
  const { deckId = "" } = useParams();
  const path = decodeDeckId(deckId);

  if (!path) {
    return <p className="text-sm text-rose-700">Missing deck path.</p>;
  }

  return (
    <div className="flex h-full min-h-0 flex-col" data-testid="present-studio">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <p className="text-[11px] uppercase tracking-wide text-teal-800">ZECT Present Studio</p>
        <div className="flex flex-wrap gap-2">
          <Link to={`/present/d/${deckId}`} className="text-xs text-teal-800" data-testid="present-studio-review-link">
            Quality review
          </Link>
          <Link to={`/present/d/${deckId}/rehearse`} className="text-xs text-teal-800" data-testid="present-open-rehearse">
            Rehearse
          </Link>
          <Link to={`/present/d/${deckId}/export`} className="text-xs text-teal-800" data-testid="present-open-export">
            Export
          </Link>
        </div>
      </div>
      <div className="min-h-0 flex-1">
        <PresentEditor pptxPath={path} variant="studio" />
      </div>
    </div>
  );
}
