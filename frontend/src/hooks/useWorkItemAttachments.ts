import { useCallback, useEffect, useState } from "react";
import { listWorkItemAttachments, type DocumentArtifactInfo } from "@/lib/api";

/** Everything attached across ASK/PLAN/AGENT for a WorkItem -- the one list
 * every Developer pane reads (not a second/third attachment store). An
 * attachment made in ASK shows up here in PLAN and AGENT without re-upload. */
export function useWorkItemAttachments(workItemId?: number | null) {
  const [attachments, setAttachments] = useState<DocumentArtifactInfo[]>([]);
  const [loading, setLoading] = useState(false);

  const reload = useCallback(() => {
    if (workItemId == null) {
      setAttachments([]);
      return;
    }
    setLoading(true);
    void listWorkItemAttachments(workItemId)
      .then((res) => setAttachments(res.attachments || []))
      .catch(() => setAttachments([]))
      .finally(() => setLoading(false));
  }, [workItemId]);

  useEffect(() => {
    reload();
  }, [reload]);

  return { attachments, loading, reload };
}
