import { useState, useEffect, useCallback } from "react";
import {
  MessageCircle, Clock, Pin, Plus, ChevronRight, ChevronLeft, X,
} from "lucide-react";
import { getConversations, createConversation, updateConversation } from "@/lib/api";

interface ConversationHistoryProps {
  mode: string;
  onSelect?: (conversationId: number, title: string) => void;
  className?: string;
}

export default function ConversationHistory({ mode, onSelect, className = "" }: ConversationHistoryProps) {
  const [conversations, setConversations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [collapsed, setCollapsed] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const res = await getConversations(mode, false, 0, 20);
      setConversations(res.items || []);
    } catch (e: any) {
      setError(e.message || "Failed to load history");
    } finally {
      setLoading(false);
    }
  }, [mode]);

  useEffect(() => { load(); }, [load]);

  const handleNew = async () => {
    try {
      const convo = await createConversation(`${mode} session`, mode);
      load();
      if (onSelect) onSelect(convo.id, convo.title);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handlePin = async (id: number, isPinned: boolean) => {
    try {
      await updateConversation(id, { is_pinned: !isPinned });
      load();
    } catch {
      // silent
    }
  };

  if (collapsed) {
    return (
      <div className={`flex flex-col items-center bg-white border border-slate-200 rounded-xl p-2 ${className}`}>
        <button
          onClick={() => setCollapsed(false)}
          className="p-1.5 text-slate-400 hover:text-slate-600 rounded"
          title="Show history"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
        <MessageCircle className="h-4 w-4 text-slate-300 mt-2" />
        <span className="text-xs text-slate-400 mt-1 [writing-mode:vertical-lr]">History</span>
      </div>
    );
  }

  return (
    <div className={`w-64 bg-white border border-slate-200 rounded-xl flex flex-col ${className}`}>
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-slate-100">
        <div className="flex items-center gap-1.5">
          <MessageCircle className="h-4 w-4 text-slate-400" />
          <span className="text-xs font-semibold text-slate-600 uppercase tracking-wide">History</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={handleNew}
            className="p-1 text-slate-400 hover:text-blue-600 rounded"
            title="New conversation"
          >
            <Plus className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => setCollapsed(true)}
            className="p-1 text-slate-400 hover:text-slate-600 rounded"
            title="Collapse"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto max-h-80">
        {loading ? (
          <div className="flex justify-center py-6">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500" />
          </div>
        ) : error ? (
          <div className="px-3 py-4 text-xs text-red-500">{error}</div>
        ) : conversations.length === 0 ? (
          <div className="px-3 py-6 text-center">
            <MessageCircle className="h-8 w-8 mx-auto text-slate-200 mb-2" />
            <p className="text-xs text-slate-400">No conversations yet</p>
            <button
              onClick={handleNew}
              className="mt-2 text-xs text-blue-600 hover:text-blue-700"
            >
              Start one
            </button>
          </div>
        ) : (
          <div className="py-1">
            {conversations.map((c: any) => (
              <button
                key={c.id}
                onClick={() => onSelect?.(c.id, c.title)}
                className="w-full text-left px-3 py-2 hover:bg-slate-50 transition-colors group"
              >
                <div className="flex items-center gap-1.5">
                  {c.is_pinned && <Pin className="h-3 w-3 text-amber-500 fill-current shrink-0" />}
                  <span className="text-xs font-medium text-slate-700 truncate flex-1">{c.title}</span>
                  <button
                    onClick={(e) => { e.stopPropagation(); handlePin(c.id, c.is_pinned); }}
                    className="hidden group-hover:block p-0.5 text-slate-300 hover:text-amber-500"
                  >
                    <Pin className="h-3 w-3" />
                  </button>
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-[10px] text-slate-400 flex items-center gap-0.5">
                    <Clock className="h-2.5 w-2.5" />
                    {c.created_at ? new Date(c.created_at).toLocaleDateString() : "—"}
                  </span>
                  <span className="text-[10px] text-slate-400">{c.message_count || 0} msgs</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
