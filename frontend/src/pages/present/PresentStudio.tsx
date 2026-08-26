import { useParams } from "react-router-dom";
import PresentEditor from "@/components/PresentEditor";
import PresentPhaseStrip from "@/pages/present/PresentPhaseStrip";
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
        <PresentPhaseStrip deckId={deckId} current="edit" />
      </div>
      <div className="min-h-0 flex-1">
        <PresentEditor pptxPath={path} variant="edit" />
      </div>
    </div>
  );
}
