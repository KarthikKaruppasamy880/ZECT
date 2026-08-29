import { useParams } from "react-router-dom";
import PresentDeckPanel from "@/components/PresentDeckPanel";
import PresentPhaseStrip from "@/pages/present/PresentPhaseStrip";
import { decodeDeckId } from "@/lib/api";

export default function PresentRehearse() {
  const { deckId = "" } = useParams();
  const path = decodeDeckId(deckId);
  return (
    <div className="space-y-3" data-testid="present-rehearse">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-slate-900">Notes &amp; rehearse</h2>
        <PresentPhaseStrip deckId={deckId} current="rehearse" />
      </div>
      <p className="text-xs text-slate-600">
        Narration lives here — not on Generate. Generation works even if Voicebox is offline. Presenter Intelligence
        uses slide text, notes, and visible chart/table/image meaning; clone/standard voice stays on this page.
      </p>
      <PresentDeckPanel variant="light" mode="companion" initialPath={path} />
    </div>
  );
}
