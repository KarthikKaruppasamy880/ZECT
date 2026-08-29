/** Map mermaid node text to Architecture explain-card ids. */

export type ArchExplainId = "client" | "lattice" | "control" | "docs";

export function explainIdFromMermaidLabel(raw: string): ArchExplainId | null {
  const t = (raw || "").toLowerCase().replace(/\s+/g, " ").trim();
  if (!t) return null;
  if (/lattice|graphify|workspace|coding engine/.test(t)) return "lattice";
  if (/client|react ui|mentrix voice|user goal|\byou\b/.test(t)) return "client";
  if (/control|agent run|ask.?plan|permissions|gates|audit|emergency stop/.test(t)) return "control";
  if (/canonical|knowledge|labs|docs|playbook|scheduled/.test(t)) return "docs";
  return null;
}
