export type ActiveRepoPrefill = {
  owner?: string;
  repo_name?: string;
  clone_branch?: string | null;
};

export function deployPrefillFromActive(
  repo: ActiveRepoPrefill | null | undefined,
  activeBranch?: string | null,
): { owner: string; repo: string; ref: string } {
  const owner = (repo?.owner || "").trim();
  const name = (repo?.repo_name || "").trim();
  const checkedOut = (activeBranch || repo?.clone_branch || "").trim();
  const ref = checkedOut || "develop";
  return { owner, repo: name, ref };
}

export function ultraReviewHref(repo: ActiveRepoPrefill | null | undefined): string {
  const owner = (repo?.owner || "zinnia").trim() || "zinnia";
  const name = (repo?.repo_name || "zoas").trim() || "zoas";
  return `/code-review?owner=${encodeURIComponent(owner)}&repo=${encodeURIComponent(name)}`;
}
