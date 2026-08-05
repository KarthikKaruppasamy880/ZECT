/** Client-side unified-diff hunk parse / apply / revert for Developer Workspace Stage C. */

export type HunkLine = { kind: " " | "+" | "-"; text: string };

export type DiffHunk = {
  id: string;
  header: string;
  oldStart: number;
  newStart: number;
  lines: HunkLine[];
};

const HUNK_RE = /^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@/;

export function parseUnifiedHunks(unified: string): DiffHunk[] {
  const lines = (unified || "").split(/\r?\n/);
  const hunks: DiffHunk[] = [];
  let current: DiffHunk | null = null;
  let idx = 0;

  for (const line of lines) {
    const m = line.match(HUNK_RE);
    if (m) {
      if (current) hunks.push(current);
      current = {
        id: `h${idx++}`,
        header: line,
        oldStart: Number(m[1]),
        newStart: Number(m[3]),
        lines: [],
      };
      continue;
    }
    if (!current) continue;
    if (line.startsWith("---") || line.startsWith("+++") || line.startsWith("diff ")) continue;
    const kind = line[0];
    if (kind === " " || kind === "+" || kind === "-") {
      current.lines.push({ kind, text: line.slice(1) });
    } else if (line === "\\ No newline at end of file") {
      continue;
    }
  }
  if (current) hunks.push(current);
  return hunks;
}

/** Apply selected hunks to `base` (old/left text). Unselected regions stay as in base. */
export function applyHunks(base: string, hunks: DiffHunk[]): string {
  if (!hunks.length) return base;
  const sorted = [...hunks].sort((a, b) => a.oldStart - b.oldStart);
  const oldLines = base.split(/\r?\n/);
  // Drop trailing empty from split if base ended without newline? keep simple: split keeps last empty if ends with \n
  const out: string[] = [];
  let cursor = 0; // 0-based index into oldLines

  for (const hunk of sorted) {
    const start = Math.max(0, hunk.oldStart - 1);
    while (cursor < start && cursor < oldLines.length) {
      out.push(oldLines[cursor++]);
    }
    for (const hl of hunk.lines) {
      if (hl.kind === " " || hl.kind === "-") {
        // consume from old
        if (cursor < oldLines.length) cursor += 1;
      }
      if (hl.kind === " " || hl.kind === "+") {
        out.push(hl.text);
      }
    }
  }
  while (cursor < oldLines.length) {
    out.push(oldLines[cursor++]);
  }
  // If original had no trailing newline and last line empty from split, trim? Prefer join with \n
  return out.join("\n");
}

/** Revert selected hunks from `current` (new/right text) back toward the old side. */
export function revertHunks(current: string, hunks: DiffHunk[]): string {
  if (!hunks.length) return current;
  const sorted = [...hunks].sort((a, b) => a.newStart - b.newStart);
  const newLines = current.split(/\r?\n/);
  const out: string[] = [];
  let cursor = 0;

  for (const hunk of sorted) {
    const start = Math.max(0, hunk.newStart - 1);
    while (cursor < start && cursor < newLines.length) {
      out.push(newLines[cursor++]);
    }
    for (const hl of hunk.lines) {
      if (hl.kind === " " || hl.kind === "+") {
        if (cursor < newLines.length) cursor += 1;
      }
      if (hl.kind === " " || hl.kind === "-") {
        out.push(hl.text);
      }
    }
  }
  while (cursor < newLines.length) {
    out.push(newLines[cursor++]);
  }
  return out.join("\n");
}
