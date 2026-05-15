import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8001";

interface SessionMessage {
  id: number;
  role: string;
  content: string;
  page: string;
  model: string;
  tokens_used: number;
  created_at: string | null;
}

interface PersistentSession {
  id: number;
  project_id: number | null;
  repo_id: number | null;
  title: string;
  status: string;
  messages_count: number;
  total_tokens: number;
  pages_visited: string;
  created_at: string | null;
  last_activity: string | null;
}

interface SessionContextType {
  session: PersistentSession | null;
  messages: SessionMessage[];
  contextSummary: string;
  loading: boolean;
  createSession: (projectId?: number, repoId?: number, title?: string) => Promise<void>;
  addMessage: (role: string, content: string, page: string, model?: string, tokens?: number) => Promise<void>;
  getContext: (page?: string) => Promise<string>;
  closeSession: () => Promise<void>;
  switchSession: (sessionId: number) => Promise<void>;
}

const SessionContext = createContext<SessionContextType>({
  session: null,
  messages: [],
  contextSummary: "",
  loading: false,
  createSession: async () => {},
  addMessage: async () => {},
  getContext: async () => "",
  closeSession: async () => {},
  switchSession: async () => {},
});

export function useSession() {
  return useContext(SessionContext);
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<PersistentSession | null>(null);
  const [messages, setMessages] = useState<SessionMessage[]>([]);
  const [contextSummary, setContextSummary] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Try to restore active session
    const savedId = localStorage.getItem("zect_session_id");
    if (savedId) {
      fetchSession(parseInt(savedId, 10));
    } else {
      fetchActiveSession();
    }
  }, []);

  const fetchSession = async (id: number) => {
    try {
      const res = await fetch(`${API}/api/persistent-sessions/${id}`);
      if (res.ok) {
        const data = await res.json();
        setSession(data);
        setMessages(data.messages || []);
        localStorage.setItem("zect_session_id", String(id));
      }
    } catch { /* ignore */ }
  };

  const fetchActiveSession = async () => {
    try {
      const res = await fetch(`${API}/api/persistent-sessions/active`);
      if (res.ok) {
        const data = await res.json();
        if (data.id) {
          setSession(data);
          localStorage.setItem("zect_session_id", String(data.id));
        }
      }
    } catch { /* ignore */ }
  };

  const createSession = useCallback(async (projectId?: number, repoId?: number, title?: string) => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/persistent-sessions/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: projectId || null, repo_id: repoId || null, title: title || "" }),
      });
      if (res.ok) {
        const data = await res.json();
        setSession(data);
        setMessages([]);
        localStorage.setItem("zect_session_id", String(data.id));
      }
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  const addMessage = useCallback(async (role: string, content: string, page: string, model = "", tokens = 0) => {
    if (!session) return;
    try {
      const res = await fetch(`${API}/api/persistent-sessions/${session.id}/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role, content, page, model, tokens_used: tokens }),
      });
      if (res.ok) {
        const msg = await res.json();
        setMessages((prev) => [...prev, { ...msg, created_at: new Date().toISOString() }]);
        setSession((prev) => prev ? { ...prev, messages_count: (prev.messages_count || 0) + 1 } : prev);
      }
    } catch { /* ignore */ }
  }, [session]);

  const getContext = useCallback(async (page?: string): Promise<string> => {
    if (!session) return "";
    try {
      const params = new URLSearchParams({ max_messages: "10" });
      if (page) params.set("page", page);
      const res = await fetch(`${API}/api/persistent-sessions/${session.id}/context?${params}`);
      if (res.ok) {
        const data = await res.json();
        setContextSummary(data.context_summary || "");
        return data.context_summary || "";
      }
    } catch { /* ignore */ }
    return "";
  }, [session]);

  const closeSession = useCallback(async () => {
    if (!session) return;
    try {
      await fetch(`${API}/api/persistent-sessions/${session.id}/close`, { method: "PATCH" });
      setSession(null);
      setMessages([]);
      setContextSummary("");
      localStorage.removeItem("zect_session_id");
    } catch { /* ignore */ }
  }, [session]);

  const switchSession = useCallback(async (sessionId: number) => {
    await fetchSession(sessionId);
  }, []);

  return (
    <SessionContext.Provider value={{ session, messages, contextSummary, loading, createSession, addMessage, getContext, closeSession, switchSession }}>
      {children}
    </SessionContext.Provider>
  );
}
