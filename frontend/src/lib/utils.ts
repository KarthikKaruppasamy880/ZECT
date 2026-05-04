import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Parse a GitHub URL or "owner/repo" string into { owner, repo }.
 * Accepts:
 *   - https://github.com/owner/repo
 *   - github.com/owner/repo
 *   - owner/repo
 *   - Just a repo name (returns as-is with empty owner)
 * Returns null if the input is empty.
 */
export function parseGitHubInput(input: string): { owner: string; repo: string } | null {
  const trimmed = input.trim();
  if (!trimmed) return null;

  // Try to parse as URL
  const urlMatch = trimmed.match(
    /(?:https?:\/\/)?(?:www\.)?github\.com\/([^/\s]+)\/([^/\s]+)/
  );
  if (urlMatch) {
    return { owner: urlMatch[1], repo: urlMatch[2].replace(/\.git$/, "") };
  }

  // Try owner/repo format
  const slashMatch = trimmed.match(/^([^/\s]+)\/([^/\s]+)$/);
  if (slashMatch) {
    return { owner: slashMatch[1], repo: slashMatch[2] };
  }

  // Just a name — return as repo with empty owner
  return { owner: "", repo: trimmed };
}
