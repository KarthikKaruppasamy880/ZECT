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
      className={`mentrix-orb relative flex items-center justify-center overflow-visible rounded-full border-4 bg-gradient-to-br shadow-2xl ${
        compact ? "h-10 w-10 sm:h-12 sm:w-12" : "h-28 w-28 sm:h-36 sm:w-36"
      } ${ORB[state]}`}
    >
      <span className="mentrix-orb-ring pointer-events-none absolute inset-[-10px] rounded-full border border-teal-400/30" data-ring="outer" />
      <span className="mentrix-orb-ring pointer-events-none absolute inset-[-4px] rounded-full border border-teal-300/40" data-ring="inner" />
      <span
        className={`mentrix-orb-core pointer-events-none absolute rounded-full bg-teal-400/20 ${compact ? "h-4 w-4" : "h-16 w-16 sm:h-20 sm:w-20"}`}
      />
      <div className="mentrix-orb-face pointer-events-none relative z-10 flex flex-col items-center" aria-hidden>
        <div className={`flex ${compact ? "gap-1" : "gap-3 sm:gap-4"}`}>
          <span className={`mentrix-orb-eye rounded-full bg-teal-100 ${compact ? "h-1.5 w-1.5" : "h-3 w-2.5 sm:h-3.5 sm:w-3"}`} />
          <span className={`mentrix-orb-eye rounded-full bg-teal-100 ${compact ? "h-1.5 w-1.5" : "h-3 w-2.5 sm:h-3.5 sm:w-3"}`} />
        </div>
        <span
          className={`mentrix-orb-mouth mt-1 rounded-full border-teal-100 ${compact ? "h-1 w-3 border" : "h-2.5 w-8 border-2 sm:h-3 sm:w-10"}`}
        />
      </div>
      <Bot
        className={`mentrix-orb-badge pointer-events-none absolute text-teal-200/80 ${
          compact ? "bottom-0 right-0 h-3 w-3" : "bottom-1 right-1 h-4 w-4 sm:h-5 sm:w-5"
        }`}
      />
    </div>
  );
}
