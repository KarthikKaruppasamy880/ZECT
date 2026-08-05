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
