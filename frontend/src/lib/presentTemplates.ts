/** Present template merge — ZECT registry cards survive empty Presenton /template/all. */

export type PresentTemplateCard = { id: string; name: string };

export function isZectRegistryTemplateId(id: string): boolean {
  return /^(zinnia-|org-|user-)/.test(id || "");
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
    if (t?.id) byId.set(t.id, { id: t.id, name: t.name || t.id });
  }
  return Array.from(byId.values());
}
