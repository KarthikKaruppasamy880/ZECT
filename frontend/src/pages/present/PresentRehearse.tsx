import { Link, useParams } from "react-router-dom";
import PresentDeckPanel from "@/components/PresentDeckPanel";
import { decodeDeckId } from "@/lib/api";

export default function PresentRehearse() {
  const { deckId = "" } = useParams();
  const path = decodeDeckId(deckId);
  return (
    <div className="space-y-3" data-testid="present-rehearse">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">Notes &amp; rehearse</h2>
        <Link to={`/present/d/${deckId}`} className="text-xs text-teal-800">
          Back to review
        </Link>
      </div>
      <p className="text-xs text-slate-600">
        Narration lives here — not on Generate. Generation works even if Voicebox is offline.
      </p>
      <PresentDeckPanel variant="light" mode="companion" initialPath={path} />
    </div>
  );
}
