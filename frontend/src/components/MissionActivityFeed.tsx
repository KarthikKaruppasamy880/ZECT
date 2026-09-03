/**
 * CP-09 -- live, reconstructable Mission activity feed.
 *
 * Replaces the old static "last 8 events as plain text" tail with a typed,
 * navigable timeline backed by the canonical Mission/EventStream SSE
 * endpoint. Seeds from whatever the parent already has (the Mission's own
 * `events`/`evidence`, so a fresh mount never shows an empty list while the
 * stream connects), then subscribes for live updates and auto-reconnects
 * with a resume cursor persisted per-mission in sessionStorage -- a tab
 * switch, route navigation, or browser refresh picks the feed back up
 * without re-fetching everything or losing the read position.
 *
 * Never renders raw model reasoning/chain-of-thought: every event's
 * `message` is already the concise, backend-built summary (tool name +
 * outcome) -- this component only adds icons/grouping/click-to-navigate on
 * top of that, it does not have access to anything more revealing.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  Bot,
  Camera,
  CheckCircle2,
  ChevronRight,
  Compass,
  FileEdit,
  FlaskConical,
  GitCompare,
  Search,
  Sparkles,
  Terminal,
  Wrench,
  XCircle,
} from "lucide-react";
import { codingAgentStreamMission, type MissionEvent } from "@/lib/api";

type Props = {
  missionId: string | null;
  initialEvents: MissionEvent[];
  /** Re-opens the stream when this changes to "running" -- e.g. right
   *  after Approve & Build/Resume/Retry moves the Mission out of a paused
   *  state, the previous SSE connection (closed once nothing was running)
   *  needs a fresh one. */
  executionState?: string;
  onOpenPath?: (path: string, line?: number) => void;
  onShowDiff?: () => void;
};

function cursorKey(missionId: string): string {
  return `zect_mission_event_cursor_${missionId}`;
}

function loadCursor(missionId: string): number {
  try {
    return Number(sessionStorage.getItem(cursorKey(missionId)) || 0) || 0;
  } catch {
    return 0;
  }
}

function saveCursor(missionId: string, seq: number): void {
  try {
    sessionStorage.setItem(cursorKey(missionId), String(seq));
  } catch {
    /* ignore quota */
  }
}

/** Coarse category per event-name prefix/keyword -- drives the icon and
 *  the click-to-navigate target. Unknown event names fall back to a
 *  generic dot rather than guessing. */
function categorize(ev: MissionEvent): {
  icon: typeof Bot;
  tone: string;
  action?: "file" | "diff" | "command" | "test" | "browser";
} {
  const name = ev.event || "";
  if (name.includes("write_file") || name.includes("apply_patch") || name === "file_diff" || name === "native_implement") {
    return { icon: FileEdit, tone: "text-teal-700", action: "diff" };
  }
  if (name === "read_file" || name === "list_dir" || name === "search_code" || name === "glob_files") {
    return { icon: Search, tone: "text-slate-500", action: "file" };
  }
  if (name === "run_command" || name === "command_output") {
    return { icon: Terminal, tone: "text-slate-600", action: "command" };
  }
  if (name.includes("test") || name.includes("quality")) {
    return { icon: FlaskConical, tone: ev.status === "error" ? "text-rose-700" : "text-slate-600", action: "test" };
  }
  if (name.startsWith("diagnose")) {
    return { icon: Wrench, tone: "text-amber-700" };
  }
  if (name.startsWith("browser_") || name.startsWith("app_")) {
    return { icon: Camera, tone: "text-indigo-700", action: "browser" };
  }
  if (name.startsWith("explore")) {
    return { icon: Compass, tone: "text-slate-500" };
  }
  if (name === "model_call" || name === "thinking") {
    return { icon: Sparkles, tone: "text-violet-700" };
  }
  if (name.includes("review") || name.includes("evidence_verify")) {
    return { icon: CheckCircle2, tone: "text-emerald-700" };
  }
  if (name === "blocked" || name.includes("write_blocked") || name.includes("validation_failed")) {
    return { icon: AlertTriangle, tone: "text-rose-700" };
  }
  if (name === "cancelled" || name === "failed") {
    return { icon: XCircle, tone: "text-rose-700" };
  }
  if (name.includes("pr") || name.includes("push") || name.includes("git")) {
    return { icon: GitCompare, tone: "text-slate-600" };
  }
  return { icon: Bot, tone: "text-slate-400" };
}

function eventPath(ev: MissionEvent): string {
  const data = ev.data || {};
  const candidate = data.path ?? data.file ?? data.rel;
  return typeof candidate === "string" ? candidate : "";
}

function eventLine(ev: MissionEvent): number | undefined {
  const data = ev.data || {};
  const line = data.line;
  return typeof line === "number" ? line : undefined;
}

function formatTime(at?: string): string {
  if (!at) return "";
  const d = new Date(at);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function dedupeAndSort(events: MissionEvent[]): MissionEvent[] {
  const bySeq = new Map<string, MissionEvent>();
  let auto = 0;
  for (const ev of events) {
    const key = ev.seq != null ? `seq:${ev.seq}` : `auto:${ev.at || ""}:${ev.event}:${auto++}`;
    bySeq.set(key, ev);
  }
  return Array.from(bySeq.values()).sort((a, b) => (a.seq || 0) - (b.seq || 0));
}

export default function MissionActivityFeed({ missionId, initialEvents, executionState, onOpenPath, onShowDiff }: Props) {
  const [events, setEvents] = useState<MissionEvent[]>(() => dedupeAndSort(initialEvents));
  const seededRef = useRef<string>("");

  // Seed from whatever the parent already fetched (mission.events) so the
  // list is never empty while the stream connects -- but only on an
  // actual mission change, not every parent re-render (which would wipe
  // out events this component already streamed in beyond what the
  // parent's last snapshot had).
  useEffect(() => {
    if (missionId && seededRef.current !== missionId) {
      seededRef.current = missionId;
      setEvents(dedupeAndSort(initialEvents));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [missionId]);

  useEffect(() => {
    if (!missionId) return;
    const controller = new AbortController();
    const cursor = Math.max(loadCursor(missionId), ...events.map((e) => e.seq || 0), 0);
    void codingAgentStreamMission(missionId, {
      after: cursor,
      signal: controller.signal,
      onEvent: (ev) => {
        setEvents((prev) => dedupeAndSort([...prev, ev]));
        if (ev.seq != null) saveCursor(missionId, ev.seq);
      },
    }).catch(() => {
      /* connection closed/aborted -- normal on unmount or Mission pause */
    });
    return () => controller.abort();
    // Re-subscribe when the Mission moves back into "running" (e.g. right
    // after an approval) -- the previous stream already auto-closed once
    // nothing was executing.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [missionId, executionState]);

  const rows = useMemo(() => events.slice(-200), [events]);

  if (!missionId) {
    return <p className="text-slate-500">Start a mission to see live activity.</p>;
  }
  if (!rows.length) {
    return <p className="text-slate-500">No activity recorded yet.</p>;
  }

  return (
    <ul className="max-h-64 space-y-0.5 overflow-auto" data-testid="mission-activity-feed">
      {rows.map((ev, i) => {
        const { icon: Icon, tone, action } = categorize(ev);
        const path = eventPath(ev);
        const line = eventLine(ev);
        const clickable = (action === "file" || action === "diff") && !!path;
        const cost = ev.estimated_cost && ev.estimated_cost > 0 ? `$${ev.estimated_cost.toFixed(4)}` : "";
        return (
          <li
            key={ev.seq ?? `${ev.at}-${i}`}
            className={`flex items-start gap-1.5 rounded px-1 py-0.5 ${clickable ? "cursor-pointer hover:bg-slate-50" : ""}`}
            onClick={() => {
              if (action === "diff" && path) {
                onOpenPath?.(path, line);
                onShowDiff?.();
              } else if (action === "file" && path) {
                onOpenPath?.(path, line);
              }
            }}
            data-testid="mission-activity-row"
            data-event={ev.event}
          >
            <Icon className={`mt-0.5 h-3 w-3 flex-shrink-0 ${tone}`} />
            <span className="min-w-0 flex-1 text-slate-700">
              <span className="text-slate-500">{formatTime(ev.at)}</span>{" "}
              {ev.role ? <span className="text-slate-400">[{ev.role}]</span> : null} {ev.message}
              {ev.model ? (
                <span className="ml-1 rounded bg-violet-50 px-1 text-[10px] text-violet-700">
                  {ev.provider ? `${ev.provider}/` : ""}
                  {ev.model}
                  {cost ? ` · ${cost}` : ""}
                </span>
              ) : null}
              {action === "browser" && ev.evidence_refs?.length ? (
                <span className="ml-1 text-[10px] text-indigo-600">
                  {ev.evidence_refs.length} evidence file{ev.evidence_refs.length > 1 ? "s" : ""}
                </span>
              ) : null}
            </span>
            {clickable ? <ChevronRight className="mt-0.5 h-3 w-3 flex-shrink-0 text-slate-300" /> : null}
          </li>
        );
      })}
    </ul>
  );
}
