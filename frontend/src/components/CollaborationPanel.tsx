import { useState, useEffect, useRef, useCallback } from "react";
import { Users, Wifi, WifiOff } from "lucide-react";
import { apiFetch, getApiBase } from "@/lib/api";

interface PresenceUser {
  user: string;
  page: string;
  connected_at: string;
}

interface CollaborationPanelProps {
  room: string;
  user?: string;
}

const USER_COLORS = [
  "text-blue-400", "text-green-400", "text-purple-400", "text-amber-400",
  "text-pink-400", "text-cyan-400", "text-red-400", "text-indigo-400",
];

function wsBase(): string {
  return getApiBase().replace(/^http/, "ws");
}

function resolvePresenceUser(explicit?: string): string {
  if (explicit && explicit !== "admin" && explicit !== "anonymous") return explicit;
  try {
    const stored = localStorage.getItem("zect_username");
    if (stored?.trim()) return stored.trim();
  } catch {
    /* ignore */
  }
  return explicit || "operator";
}

export default function CollaborationPanel({ room, user }: CollaborationPanelProps) {
  const presenceUser = resolvePresenceUser(user);
  const [connected, setConnected] = useState(false);
  const [users, setUsers] = useState<PresenceUser[]>([]);
  const [activeCount, setActiveCount] = useState(0);
  const [backendReady, setBackendReady] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout>>();
  const failCountRef = useRef(0);
  const disabledRef = useRef(false);

  const fetchPresence = useCallback(async () => {
    if (typeof localStorage !== "undefined" && !localStorage.getItem("zect_token")) return;
    try {
      const res = await apiFetch(`/api/realtime/presence/${encodeURIComponent(room)}`);
      if (res.status === 401 || res.status === 404) {
        disabledRef.current = true;
        return;
      }
      if (res.ok) {
        const data = await res.json();
        setUsers(data.users || []);
        setActiveCount(data.active_users || 0);
      }
    } catch {
      /* ignore */
    }
  }, [room]);

  const connect = useCallback(() => {
    if (!backendReady || disabledRef.current) return;
    if (typeof localStorage !== "undefined" && !localStorage.getItem("zect_token")) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    if (failCountRef.current >= 3) return;

    const ws = new WebSocket(`${wsBase()}/ws/${encodeURIComponent(room)}?user=${encodeURIComponent(presenceUser)}`);

    ws.onopen = () => {
      failCountRef.current = 0;
      setConnected(true);
      ws.send(JSON.stringify({ type: "page_change", page: window.location.pathname }));
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "presence") {
          setActiveCount(data.active_users || 0);
          void fetchPresence();
        }
      } catch {
        /* ignore */
      }
    };

    ws.onclose = () => {
      setConnected(false);
      failCountRef.current += 1;
      if (disabledRef.current || failCountRef.current >= 3) return;
      const delay = Math.min(30_000, 3000 * failCountRef.current);
      reconnectRef.current = setTimeout(connect, delay);
    };

    ws.onerror = () => {
      setConnected(false);
    };

    wsRef.current = ws;
  }, [backendReady, room, presenceUser, fetchPresence]);

  useEffect(() => {
    let cancelled = false;
    apiFetch("/api/auth/config")
      .then((res) => {
        if (!cancelled && res.ok) setBackendReady(true);
      })
      .catch(() => {
        if (!cancelled) setBackendReady(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!backendReady) return;
    connect();
    const onVis = () => {
      if (document.visibilityState === "visible" && !disabledRef.current) {
        connect();
      }
    };
    document.addEventListener("visibilitychange", onVis);
    return () => {
      document.removeEventListener("visibilitychange", onVis);
      clearTimeout(reconnectRef.current);
      wsRef.current?.close();
    };
  }, [backendReady, connect]);

  useEffect(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "page_change", page: window.location.pathname }));
    }
  }, []);

  useEffect(() => {
    if (!connected) return;
    const id = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "ping" }));
      }
    }, 30000);
    return () => clearInterval(id);
  }, [connected]);

  const colorClass = USER_COLORS[presenceUser.length % USER_COLORS.length];
  const count = activeCount || users.length;

  return (
    <div
      className="flex items-center gap-2 text-xs text-slate-500"
      data-testid="collaboration-panel"
      title="Live presence — who is currently using ZECT (not Wi‑Fi or Zoom)"
    >
      {connected ? (
        <Wifi className={`h-3.5 w-3.5 ${colorClass}`} aria-hidden />
      ) : (
        <WifiOff className="h-3.5 w-3.5 text-slate-400" aria-hidden />
      )}
      <Users className="h-3.5 w-3.5" aria-hidden />
      <span data-testid="presence-label">
        {connected ? `Presence: ${count}` : "Presence: Offline"}
      </span>
    </div>
  );
}
