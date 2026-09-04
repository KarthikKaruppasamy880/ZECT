import { useWorkItemAttachments } from "@/hooks/useWorkItemAttachments";

/** Renders whatever is durably attached to this WorkItem, however it got
 * there -- ASK, PLAN, or AGENT. The one visibility surface for item 2 of the
 * UX-continuity acceptance tranche: an attachment made in one tab must be
 * visible in the others without re-upload. */
export function WorkItemAttachmentsStrip({ workItemId }: { workItemId?: number | null }) {
  const { attachments } = useWorkItemAttachments(workItemId);
  if (!attachments.length) return null;
  return (
    <p className="mt-1 flex flex-wrap items-center gap-1 text-[10px] text-slate-500" data-testid="mentrix-coding-agent-workitem-attachments">
      <span className="text-slate-400">Attached to this Mission:</span>
      {attachments.map((a) => (
        <span
          key={a.id}
          className="rounded bg-slate-100 px-1.5 py-0.5 text-slate-600"
          data-testid="mentrix-coding-agent-workitem-attachment-chip"
          title={a.filename}
        >
          [{a.kind === "image" ? "image" : "doc"}] {a.filename}
        </span>
      ))}
    </p>
  );
}
