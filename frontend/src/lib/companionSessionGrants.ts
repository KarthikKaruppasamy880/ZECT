/** Capability names minted after Companion Allow — must match backend CAPABILITY_TO_ACTIONS. */

export function sessionCapsForTools(tools: string[]): string[] {
  const caps = new Set<string>();
  for (const t of tools) {
    if (t.startsWith("browser_")) {
      caps.add("browser:control");
      caps.add("desktop:control");
    } else if (t.startsWith("computer_") || t.startsWith("desktop_") || t === "file_organize_approve") {
      caps.add("desktop:control");
    }
    if (t === "desktop_list_dir" || t === "desktop_read") {
      caps.add("desktop:view");
      caps.add("filesystem:scan");
    }
    if (t === "file_organize_approve" || t === "desktop_move_path" || t === "desktop_mkdir") {
      caps.add("filesystem:move");
    }
    if (t === "email_send" || t === "email_digest") {
      caps.add(t === "email_send" ? "email:draft" : "email:read");
    }
    if (t === "slack_digest") caps.add("slack:read");
    if (t === "jira_get_issue" || t === "jira_search_incidents") caps.add("jira:read");
  }
  return [...caps];
}
