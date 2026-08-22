import { Bot } from "lucide-react";
import { ORB, type AvatarState } from "@/mentrix/MentrixSessionContext";

type MentrixAvatarOrbProps = {
  state: AvatarState;
  compact?: boolean;
};

export default function MentrixAvatarOrb({ state, compact = false }: MentrixAvatarOrbProps) {
  return (
    <div
      data-testid="mentrix-avatar"
      data-state={state}
      className={`mentrix-orb relative flex items-center justify-center rounded-full border-4 bg-gradient-to-br shadow-2xl ${
        compact ? "h-10 w-10 sm:h-12 sm:w-12" : "h-16 w-16 sm:h-24 sm:w-24"
      } ${ORB[state]}`}
    >
      <span className="mentrix-orb-ring pointer-events-none absolute inset-[-6px] rounded-full border border-teal-400/30" data-ring="outer" />
      <span className="mentrix-orb-ring pointer-events-none absolute inset-[-2px] rounded-full border border-teal-300/40" data-ring="inner" />
      <span className={`mentrix-orb-core pointer-events-none absolute rounded-full bg-teal-400/20 ${compact ? "h-4 w-4" : "h-8 w-8"}`} />
      <Bot className={compact ? "relative h-5 w-5 text-teal-300" : "relative h-8 w-8 text-teal-300 sm:h-12 sm:w-12"} />
    </div>
  );
}
