import { Link } from "react-router-dom";

export type PresentPhase = "edit" | "quality" | "rehearse" | "export";

export default function PresentPhaseStrip({
  deckId,
  current,
}: {
  deckId: string;
  current: PresentPhase;
}) {
  const items: Array<{ id: PresentPhase; to: string; label: string; testId: string }> = [
    { id: "edit", to: `/present/d/${deckId}/edit`, label: "Edit", testId: "present-studio-phase-edit" },
    { id: "quality", to: `/present/d/${deckId}`, label: "Quality", testId: "present-studio-review-link" },
    { id: "rehearse", to: `/present/d/${deckId}/rehearse`, label: "Rehearse", testId: "present-open-rehearse" },
    { id: "export", to: `/present/d/${deckId}/export`, label: "Export", testId: "present-open-export" },
  ];
  return (
    <nav
      className="flex flex-wrap gap-1"
      data-testid="present-studio-phases"
      aria-label="Present journey"
    >
      {items.map((item) => (
        <Link
          key={item.id}
          to={item.to}
          data-testid={item.testId}
          aria-current={current === item.id ? "page" : undefined}
          className={`inline-flex min-h-11 items-center rounded-md px-3 py-2 text-xs ${
            current === item.id ? "bg-teal-700 text-white" : "text-teal-800 hover:bg-teal-50"
          }`}
        >
          {item.label}
        </Link>
      ))}
    </nav>
  );
}
