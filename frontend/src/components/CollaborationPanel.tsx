import { useState, useEffect, useRef, useCallback } from "react";
import { Users, Wifi, WifiOff } from "lucide-react";
import { apiFetch } from "@/lib/api";

const WS_BASE = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/^http/, "ws");

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

export default function CollaborationPanel({ room, user = "anonymous" }: CollaborationPanelProps) {
  const [connected, setConnected] = useState(false);
  const [users, setUsers] = useState<PresenceUser[]>([]);
  const [activeCount, setActiveCount] = useState(0);
  const [backendReady, setBackendReady] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout>>();
  const failCountRef = useRef(0);

  const connect = useCallback(() => {
    if (!backendReady) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    if (failCountRef.current >= 3) return;

    const ws = new WebSocket(`${WS_BASE}/ws/${room}?user=${encodeURIComponent(user)}`);

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
          fetchPresence();
        } else if (data.type === "pong") {
          // keep-alive
        }
      } catch { /* ignore */ }
    };

    ws.onclose = () => {
      setConnected(false);
      failCountRef.current += 1;
      if (failCountRef.current < 3) {
        reconnectRef.current = setTimeout(connect, 8000);
      }
    };

    ws.onerror = () => {
      setConnected(false);
    };

    wsRef.current = ws;
  }, [backendReady, room, user]);

  const fetchPresence = async () => {
    try {
      const res = await apiFetch(`/api/realtime/presence/${room}`);
      if (res.ok) {
        const data = await res.json();
        setUsers(data.users || []);
        setActiveCount(data.active_users || 0);
      }
    } catch {
      /* ignore */
    }
  };

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
    return () => {
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

  const colorClass = USER_COLORS[user.length % USER_COLORS.length];

  return (
    <div className="flex items-center gap-2 text-xs text-slate-500" data-testid="collaboration-panel">
      {connected ? (
        <Wifi className={`h-3.5 w-3.5 ${colorClass}`} />
      ) : (
        <WifiOff className="h-3.5 w-3.5 text-slate-400" />
      )}
      <Users className="h-3.5 w-3.5" />
      <span>{activeCount || users.length} online</span>
    </div>
  );
}
