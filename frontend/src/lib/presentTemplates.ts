/** Present template merge — ZECT registry cards survive empty Presenton /template/all. */

export type PresentTemplateCard = {
  id: string;
  name: string;
  native_ready?: boolean;
  visual?: { ready?: boolean };
};

export function isZectRegistryTemplateId(id: string): boolean {
  return /^(zinnia-|org-|user-)/.test(id || "");
}

/** Generate dropdown: engine builtins when Presenton is up; registry only when READY. */
export function isGenerateTemplateReady(
  t: PresentTemplateCard,
  opts?: { presentonReady?: boolean },
): boolean {
  if (!t?.id) return false;
  if (t.id === "__custom__") return Boolean(opts?.presentonReady);
  if (!isZectRegistryTemplateId(t.id)) return Boolean(opts?.presentonReady);
  return Boolean(t.native_ready || t.visual?.ready);
}

export function mergePresentTemplateLists(
  builtin: PresentTemplateCard[],
  remotePresenton: PresentTemplateCard[],
  registry: PresentTemplateCard[],
  previous: PresentTemplateCard[] = [],
): PresentTemplateCard[] {
  const byId = new Map<string, PresentTemplateCard>();
  for (const t of builtin) {
    if (t?.id) byId.set(t.id, t);
  }
  for (const t of previous) {
    if (t?.id && isZectRegistryTemplateId(t.id)) byId.set(t.id, t);
  }
  for (const t of remotePresenton) {
    if (!t?.id || isZectRegistryTemplateId(t.id)) continue;
    byId.set(t.id, t);
  }
  for (const t of registry) {
    if (t?.id) byId.set(t.id, { ...t, id: t.id, name: t.name || t.id });
  }
  return Array.from(byId.values());
}
