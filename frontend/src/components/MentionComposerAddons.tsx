/**
 * Developer composer @mention autocomplete + resolved-context display.
 * Deliberately a simple inline list under the textarea rather than a
 * floating cursor-position popup -- real and functional, not a fake
 * decorative affordance, just a smaller visual surface than a full IDE
 * mention picker.
 */
import { useMemo } from "react";
import type { RefObject } from "react";
import { MENTION_TYPES, applyMention, detectMentionTrigger, type MentionType } from "@/lib/mentions";
import type { ContextPack } from "@/lib/api";

export function MentionAutocomplete({
  value,
  onChange,
  textareaRef,
}: {
  value: string;
  onChange: (next: string, cursor: number) => void;
  textareaRef: RefObject<HTMLTextAreaElement | HTMLInputElement | null>;
}) {
  const cursor = textareaRef.current?.selectionStart ?? value.length;
  const trigger = useMemo(() => detectMentionTrigger(value, cursor), [value, cursor]);
  if (!trigger) return null;
  const candidates = MENTION_TYPES.filter((m) => m.type.startsWith(trigger.query));
  if (!candidates.length) return null;

  const pick = (type: MentionType, needsValue: boolean) => {
    const { text, cursor: nextCursor } = applyMention(value, trigger.start, cursor, type, needsValue);
    onChange(text, nextCursor);
    requestAnimationFrame(() => {
      const el = textareaRef.current;
      if (el) {
        el.focus();
        el.setSelectionRange(nextCursor, nextCursor);
      }
    });
  };

  return (
    <div
      className="mt-1 max-h-32 overflow-auto rounded border border-slate-200 bg-white text-[11px] shadow-sm"
      data-testid="mention-autocomplete"
    >
      {candidates.map((m) => (
        <button
          key={m.type}
          type="button"
          data-testid={`mention-option-${m.type}`}
          className="block w-full px-2 py-1 text-left hover:bg-slate-50"
          onClick={() => pick(m.type, m.needsValue)}
        >
          <span className="font-mono text-teal-700">@{m.type}</span>
          <span className="ml-2 text-slate-500">{m.hint}</span>
        </button>
      ))}
    </div>
  );
}

export function MentionContextStrip({ pack }: { pack: ContextPack | null }) {
  if (!pack || !pack.items.length) return null;
  const resolved = pack.items.filter((i) => i.verification_state !== "unresolved");
  const unresolved = pack.items.filter((i) => i.verification_state === "unresolved");
  return (
    <div
      className="mt-1 rounded border border-slate-100 bg-slate-50 px-2 py-1 text-[10px] text-slate-600"
      data-testid="mention-context-strip"
    >
      <span className="font-medium">
        Context used ({pack.token_used}/{pack.token_budget} tokens):
      </span>{" "}
      {resolved.length
        ? resolved.map((i) => `${i.source_type}:${i.source_id}`).join(", ")
        : "none resolved"}
      {unresolved.length ? (
        <span className="text-amber-700" data-testid="mention-context-unresolved">
          {" "}
          · unresolved: {unresolved.map((i) => `${i.source_type}:${i.source_id}`).join(", ")}
        </span>
      ) : null}
    </div>
  );
}
