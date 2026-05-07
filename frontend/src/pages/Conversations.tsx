import { useState, useEffect, useCallback } from "react";
import {
  MessageCircle, Plus, Trash2, Archive, Pin, Send, X, Clock, Star,
} from "lucide-react";
import {
  getConversations, createConversation, updateConversation,
  deleteConversation, addConversationMessage, getConversationMessages,
} from "@/lib/api";

const MODES = ["ask", "plan", "build", "review", "deploy"];

export default function Conversations() {
  const [conversations, setConversations] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filterMode, setFilterMode] = useState("");
  const [showArchived, setShowArchived] = useState(false);
  const [activeConvo, setActiveConvo] = useState<any>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [newMessage, setNewMessage] = useState("");
  const [showNew, setShowNew] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newMode, setNewMode] = useState("ask");

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const res = await getConversations(filterMode || undefined, showArchived);
      setConversations(res.items || []);
      setTotal(res.total || 0);
    } catch (e: any) {
      setError(e.message || "Failed to load conversations");
    } finally {
      setLoading(false);
    }
  }, [filterMode, showArchived]);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async () => {
    if (!newTitle.trim()) return;
    try {
      const convo = await createConversation(newTitle, newMode);
      setShowNew(false);
      setNewTitle("");
      setNewMode("ask");
      setActiveConvo(convo);
      setMessages([]);
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this conversation?")) return;
    try {
      await deleteConversation(id);
      if (activeConvo?.id === id) { setActiveConvo(null); setMessages([]); }
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleTogglePin = async (convo: any) => {
    try {
      await updateConversation(convo.id, { is_pinned: !convo.is_pinned });
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleToggleArchive = async (convo: any) => {
    try {
      await updateConversation(convo.id, { is_archived: !convo.is_archived });
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const openConvo = async (convo: any) => {
    setActiveConvo(convo);
    try {
      const msgs = await getConversationMessages(convo.id);
      setMessages(msgs || []);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleSendMessage = async () => {
    if (!newMessage.trim() || !activeConvo) return;
    try {
      await addConversationMessage(activeConvo.id, "user", newMessage);
      setNewMessage("");
      const msgs = await getConversationMessages(activeConvo.id);
      setMessages(msgs || []);
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <MessageCircle className="h-6 w-6 text-blue-600" /> Conversations
          </h1>
          <p className="text-sm text-slate-500 mt-1">{total} conversations — session history across all modes</p>
        </div>
        <button
          onClick={() => setShowNew(true)}
          className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
        >
          <Plus className="h-4 w-4" /> New Conversation
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">{error}</div>
      )}

      {/* Filters */}
      <div className="flex gap-2 items-center flex-wrap">
        <button
          onClick={() => setFilterMode("")}
          className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
            !filterMode ? "bg-blue-100 text-blue-700" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
          }`}
        >
          All
        </button>
        {MODES.map(m => (
          <button
            key={m}
            onClick={() => setFilterMode(filterMode === m ? "" : m)}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors capitalize ${
              filterMode === m ? "bg-blue-100 text-blue-700" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            {m}
          </button>
        ))}
        <button
          onClick={() => setShowArchived(!showArchived)}
          className={`ml-auto px-3 py-1 rounded-full text-xs font-medium transition-colors ${
            showArchived ? "bg-amber-100 text-amber-700" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
          }`}
        >
          <Archive className="h-3 w-3 inline mr-1" /> {showArchived ? "Showing Archived" : "Show Archived"}
        </button>
      </div>

      {/* New Conversation Form */}
      {showNew && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-slate-900">New Conversation</h3>
            <button onClick={() => setShowNew(false)} className="text-slate-400 hover:text-slate-600"><X className="h-5 w-5" /></button>
          </div>
          <div className="flex gap-3">
            <input
              type="text"
              placeholder="Conversation title"
              value={newTitle}
              onChange={e => setNewTitle(e.target.value)}
              className="flex-1 px-4 py-2 border border-slate-300 rounded-lg text-sm"
              onKeyDown={e => e.key === "Enter" && handleCreate()}
            />
            <select
              value={newMode}
              onChange={e => setNewMode(e.target.value)}
              className="px-4 py-2 border border-slate-300 rounded-lg text-sm"
            >
              {MODES.map(m => (
                <option key={m} value={m}>{m.charAt(0).toUpperCase() + m.slice(1)}</option>
              ))}
            </select>
            <button
              onClick={handleCreate}
              disabled={!newTitle.trim()}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm disabled:opacity-50"
            >
              Create
            </button>
          </div>
        </div>
      )}

      <div className="grid md:grid-cols-3 gap-6">
        {/* Conversation List */}
        <div className="md:col-span-1 space-y-2">
          {loading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600" />
            </div>
          ) : conversations.length === 0 ? (
            <div className="text-center py-8 text-slate-500">
              <MessageCircle className="h-10 w-10 mx-auto mb-2 text-slate-300" />
              <p className="text-sm">No conversations yet</p>
            </div>
          ) : (
            conversations.map((c: any) => (
              <div
                key={c.id}
                onClick={() => openConvo(c)}
                className={`bg-white border rounded-xl p-3 cursor-pointer transition-all ${
                  activeConvo?.id === c.id ? "border-blue-400 shadow-sm" : "border-slate-200 hover:border-slate-300"
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      {c.is_pinned && <Star className="h-3 w-3 text-amber-500 fill-current" />}
                      <h4 className="text-sm font-medium text-slate-900 truncate">{c.title}</h4>
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="px-1.5 py-0.5 bg-blue-50 text-blue-600 rounded text-xs capitalize">{c.mode}</span>
                      <span className="text-xs text-slate-400">{c.message_count || 0} msgs</span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1 flex items-center gap-1">
                      <Clock className="h-3 w-3" /> {c.created_at ? new Date(c.created_at).toLocaleDateString() : "—"}
                    </p>
                  </div>
                  <div className="flex flex-col gap-0.5 ml-2">
                    <button onClick={e => { e.stopPropagation(); handleTogglePin(c); }} className="p-1 text-slate-300 hover:text-amber-500">
                      <Pin className="h-3 w-3" />
                    </button>
                    <button onClick={e => { e.stopPropagation(); handleToggleArchive(c); }} className="p-1 text-slate-300 hover:text-amber-600">
                      <Archive className="h-3 w-3" />
                    </button>
                    <button onClick={e => { e.stopPropagation(); handleDelete(c.id); }} className="p-1 text-slate-300 hover:text-red-500">
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Message View */}
        <div className="md:col-span-2 bg-white border border-slate-200 rounded-xl overflow-hidden flex flex-col" style={{ minHeight: 400 }}>
          {activeConvo ? (
            <>
              <div className="border-b border-slate-200 px-5 py-3">
                <h3 className="font-semibold text-slate-900">{activeConvo.title}</h3>
                <p className="text-xs text-slate-500 capitalize">{activeConvo.mode} mode</p>
              </div>
              <div className="flex-1 overflow-y-auto p-5 space-y-3">
                {messages.length === 0 ? (
                  <p className="text-sm text-slate-400 text-center py-8">No messages yet. Start the conversation!</p>
                ) : (
                  messages.map((m: any, idx: number) => (
                    <div key={idx} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                      <div className={`max-w-[80%] rounded-xl px-4 py-2.5 text-sm ${
                        m.role === "user" ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-800"
                      }`}>
                        <p className="whitespace-pre-wrap">{m.content}</p>
                        <p className={`text-xs mt-1 ${m.role === "user" ? "text-blue-200" : "text-slate-400"}`}>
                          {m.created_at ? new Date(m.created_at).toLocaleTimeString() : ""}
                          {m.tokens_used ? ` · ${m.tokens_used} tokens` : ""}
                        </p>
                      </div>
                    </div>
                  ))
                )}
              </div>
              <div className="border-t border-slate-200 p-3">
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Type a message..."
                    value={newMessage}
                    onChange={e => setNewMessage(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && handleSendMessage()}
                    className="flex-1 px-4 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                  <button
                    onClick={handleSendMessage}
                    disabled={!newMessage.trim()}
                    className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm disabled:opacity-50"
                  >
                    <Send className="h-4 w-4" /> Send
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-400">
              <div className="text-center">
                <MessageCircle className="h-12 w-12 mx-auto mb-3 text-slate-300" />
                <p className="text-sm">Select a conversation to view messages</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
