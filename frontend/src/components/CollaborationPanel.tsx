import { useState, useEffect, useRef, useCallback } from "react";
import { Users, Wifi, WifiOff } from "lucide-react";

const WS_BASE = (import.meta.env.VITE_API_URL || "http://localhost:8001").replace(/^http/, "ws");

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
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout>>();

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(`${WS_BASE}/ws/${room}?user=${encodeURIComponent(user)}`);

    ws.onopen = () => {
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
      reconnectRef.current = setTimeout(connect, 5000);
    };

    ws.onerror = () => {
      setConnected(false);
    };

    wsRef.current = ws;
  }, [room, user]);

  const fetchPresence = async () => {
    const API = import.meta.env.VITE_API_URL || "http://localhost:8001";
    try {
      const res = await fetch(`${API}/api/realtime/presence/${room}`);
      if (res.ok) {
        const data = await res.json();
        setUsers(data.users || []);
        setActiveCount(data.active_users || 0);
      }
    } catch { /* ignore */ }
  };

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  // Send page change on navigation
  useEffect(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "page_change", page: window.location.pathname }));
    }
  }, []);

  // Ping keep-alive
  useEffect(() => {
    const interval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "ping" }));
      }
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 rounded-lg border border-slate-700">
      {connected ? (
        <Wifi className="w-3.5 h-3.5 text-green-400" />
      ) : (
        <WifiOff className="w-3.5 h-3.5 text-red-400" />
      )}
      <Users className="w-3.5 h-3.5 text-slate-400" />
      <span className="text-xs text-slate-300">{activeCount}</span>
      <div className="flex -space-x-1">
        {users.slice(0, 5).map((u, i) => (
          <div
            key={`${u.user}-${i}`}
            className={`w-5 h-5 rounded-full bg-slate-700 border border-slate-600 flex items-center justify-center ${USER_COLORS[i % USER_COLORS.length]}`}
            title={`${u.user} on ${u.page || "unknown"}`}
          >
            <span className="text-[8px] font-bold uppercase">{u.user.charAt(0)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
