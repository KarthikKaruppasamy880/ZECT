/** Path helpers for the developer workspace — keep writes inside the active root. */

export function normalizePath(p: string): string {
  return (p || "").replace(/\\/g, "/").replace(/\/+/g, "/").replace(/\/$/, "") || "/";
}

/**
 * True when `candidate` is the same as `root` or a descendant of `root`.
 * Case-insensitive on Windows-style drive letters.
 */
export function isPathInsideRoot(candidate: string, root: string): boolean {
  const c = normalizePath(candidate);
  const r = normalizePath(root);
  if (!r || r === "/") return false;
  const cl = c.toLowerCase();
  const rl = r.toLowerCase();
  return cl === rl || cl.startsWith(rl + "/");
}

export function languageFromPath(path: string): string {
  const ext = path.split(".").pop()?.toLowerCase() || "";
  const map: Record<string, string> = {
    ts: "typescript",
    tsx: "typescript",
    js: "javascript",
    jsx: "javascript",
    py: "python",
    json: "json",
    md: "markdown",
    css: "css",
    html: "html",
    yml: "yaml",
    yaml: "yaml",
    rs: "rust",
    go: "go",
    java: "java",
    sh: "shell",
    sql: "sql",
  };
  return map[ext] || "plaintext";
}

/** Relative path of `candidate` under `root`, or null if outside. */
export function relativeToRoot(candidate: string, root: string): string | null {
  if (!isPathInsideRoot(candidate, root)) return null;
  const c = normalizePath(candidate);
  const r = normalizePath(root);
  if (c.toLowerCase() === r.toLowerCase()) return "";
  return c.slice(r.length + 1);
}

/** True when path (abs or rel) matches any marker entry (abs or rel under root). */
export function pathMatchesMarker(filePath: string, root: string, markers: Iterable<string>): boolean {
  const rel = relativeToRoot(filePath, root);
  const normFile = normalizePath(filePath).toLowerCase();
  const normRel = (rel ?? "").toLowerCase();
  for (const m of markers) {
    const nm = normalizePath(m).toLowerCase();
    if (!nm) continue;
    if (nm === normFile || (normRel && (nm === normRel || nm.endsWith("/" + normRel)))) return true;
    if (isPathInsideRoot(m, root) && normalizePath(m).toLowerCase() === normFile) return true;
  }
  return false;
}
