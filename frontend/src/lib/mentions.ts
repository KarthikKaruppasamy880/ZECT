/** Developer composer @mentions — shared parsing/detection used by the
 * autocomplete dropdown and by the pre-send "resolve real context" step.
 * Must stay in sync with backend/app/services/coding_engine/mention_resolver.py's
 * supported types. */

export type MentionType =
  | "file" | "folder" | "symbol" | "references" | "repo" | "plan"
  | "diff" | "terminal" | "error" | "test" | "lattice" | "skill" | "rule";

export const MENTION_TYPES: { type: MentionType; needsValue: boolean; hint: string }[] = [
  { type: "file", needsValue: true, hint: "read a workspace file" },
  { type: "folder", needsValue: true, hint: "list a workspace folder" },
  { type: "symbol", needsValue: true, hint: "look up a symbol in Lattice" },
  { type: "references", needsValue: true, hint: "find references via Lattice" },
  { type: "repo", needsValue: true, hint: "attached repository by id" },
  { type: "plan", needsValue: true, hint: "a saved PLAN.md by id" },
  { type: "diff", needsValue: false, hint: "current workspace git diff" },
  { type: "terminal", needsValue: true, hint: "output of a running process" },
  { type: "error", needsValue: false, hint: "most recent recorded failure" },
  { type: "test", needsValue: false, hint: "most recent test results" },
  { type: "lattice", needsValue: true, hint: "search the Lattice graph" },
  { type: "skill", needsValue: true, hint: "a registered skill" },
  { type: "rule", needsValue: false, hint: "ZECT.md/AGENTS.md/.zect/rules" },
];

// No /g flag: hasMentions only needs a boolean .test(), and a global-flagged
// regex's .test() mutates its own lastIndex across calls -- reusing one
// module-level instance would make the SECOND call on the same string return
// false right after the first returned true. (Found by a test flake, not by
// inspection -- worth keeping this comment so it isn't reintroduced.)
const MENTION_RE = /@(file|folder|symbol|references|repo|plan|diff|terminal|error|test|lattice|skill|rule)(?::(\S+))?/;

/** True if the text has at least one recognized @mention worth resolving. */
export function hasMentions(text: string): boolean {
  return MENTION_RE.test(text || "");
}

/** Find the in-progress "@partial" token right before the cursor, if any —
 * drives the autocomplete dropdown. Returns null when the cursor isn't
 * inside a fresh @mention (e.g. mid-word, or after a completed one). */
export function detectMentionTrigger(
  text: string,
  cursor: number,
): { query: string; start: number } | null {
  const upTo = text.slice(0, cursor);
  const at = upTo.lastIndexOf("@");
  if (at === -1) return null;
  const between = upTo.slice(at + 1);
  if (/\s/.test(between)) return null; // already moved past the mention token
  return { query: between.toLowerCase(), start: at };
}

/** Replace the in-progress "@partial" token with a completed mention. */
export function applyMention(
  text: string,
  start: number,
  cursor: number,
  type: MentionType,
  needsValue: boolean,
): { text: string; cursor: number } {
  const inserted = needsValue ? `@${type}:` : `@${type} `;
  const next = text.slice(0, start) + inserted + text.slice(cursor);
  return { text: next, cursor: start + inserted.length };
}
