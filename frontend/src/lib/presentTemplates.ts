/** Present template merge — ZECT registry cards survive empty engine template lists. */

export type PresentTemplateCard = {
  id: string;
  name: string;
  native_ready?: boolean;
  visual?: { ready?: boolean };
};

export function isZectRegistryTemplateId(id: string): boolean {
  return /^(zinnia-|org-|user-)/.test(id || "");
}

/** Generate dropdown: engine builtins when presentation engine is up; registry only when READY. */
export function isGenerateTemplateReady(
  t: PresentTemplateCard,
  opts?: { engineReady?: boolean; /** @deprecated */ presentonReady?: boolean },
): boolean {
  const engineReady = opts?.engineReady ?? opts?.presentonReady;
  if (!t?.id) return false;
  if (t.id === "__custom__") return Boolean(engineReady);
  if (!isZectRegistryTemplateId(t.id)) return Boolean(engineReady);
  return Boolean(t.native_ready || t.visual?.ready);
}

/**
 * Gallery list: canonical Zinnia cards stay visible (badge may say TEMPLATE_NOT_READY).
 * Generate stays READY-gated via isGenerateTemplateReady. hideNotReady only filters org/user uploads.
 */
export function isGalleryTemplateVisible(
  t: PresentTemplateCard,
  hideNotReady: boolean,
): boolean {
  if (!t?.id) return false;
  if (t.id.startsWith("zinnia-")) return true;
  if (!hideNotReady) return true;
  return Boolean(t.visual?.ready ?? t.native_ready);
}

/** Builtin gallery shells are not in the upload registry — hide Delete. */
export function canDeleteGalleryTemplate(id: string): boolean {
  if (!id) return false;
  if (id.startsWith("zinnia-")) return false;
  if (id === "org-standard" || id === "org-delivery") return false;
  return id.startsWith("user-") || id.startsWith("org-");
}

export function mergePresentTemplateLists(
  builtin: PresentTemplateCard[],
  remoteEngine: PresentTemplateCard[],
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
  for (const t of remoteEngine) {
    if (!t?.id || isZectRegistryTemplateId(t.id)) continue;
    byId.set(t.id, t);
  }
  for (const t of registry) {
    if (t?.id) byId.set(t.id, { ...t, id: t.id, name: t.name || t.id });
  }
  return Array.from(byId.values());
}
