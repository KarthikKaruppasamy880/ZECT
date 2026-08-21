/** Prefer a saved clone over leftover stock Echo unless the operator explicitly locked stock/none. */

export function preferredPresentVoiceChoice(
  stored: string,
  cloneVoiceId: string | undefined,
  userLockedStockOrNone: boolean,
): string {
  if (userLockedStockOrNone) return stored;
  if (cloneVoiceId && (!stored.trim() || stored.startsWith("stock:"))) {
    return `clone:${cloneVoiceId}`;
  }
  return stored;
}
