import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { askQuestion, saveContext, loadContext, clearContext } from "@/lib/api";
import { useWorkspaceRepoContext } from "@/hooks/useWorkspaceRepoContext";
import { contextPageFor } from "@/lib/workspaceContext";
import CodeOutput from "@/components/CodeOutput";
import ModelSelector from "@/components/ModelSelector";
import PromptHygieneTips from "@/components/PromptHygieneTips";
import ConversationHistory from "@/components/ConversationHistory";
import AttachedContextPanel, { type AttachedFile } from "@/components/AttachedContextPanel";
import PhaseErrorBanner from "@/components/PhaseErrorBanner";
import {
  MessageSquare,
  Send,
  Loader2,
  Bot,
  User,
  Copy,
  Check,
  ArrowRight,
} from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
  tokens?: number;
  model?: string;
}

export default function AskMode() {
  const navigate = useNavigate();
  const location = useLocation();
  const {
    activeRepoId,
    projectKey,
    blueprintPrompt,
    loadSavedBlueprint,
    clearBlueprintContext,
    loadBlueprintPrompt,
  } = useWorkspaceRepoContext();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [repoContext, setRepoContext] = useState("");
  const [selectedModel, setSelectedModel] = useState("gpt-4o-mini");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedMsgIdx, setCopiedMsgIdx] = useState<number | null>(null);
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([]);

  useEffect(() => {
    void (async () => {
      const state = location.state as { repoContext?: string; question?: string } | null;
      let ctx = state?.repoContext || "";
      if (!ctx && projectKey) {
        const session = await loadContext(contextPageFor("workspace", projectKey), ["blueprint_prompt", "repo_analysis"]).catch(() => null);
        ctx =
          session?.entries.find((e) => e.key === "blueprint_prompt")?.value ||
          session?.entries.find((e) => e.key === "repo_analysis")?.value ||
          "";
      }
      if (!ctx && blueprintPrompt) ctx = blueprintPrompt;
      if (!ctx) {
        const saved = await loadSavedBlueprint();
        if (saved) ctx = saved;
      }
      setRepoContext(ctx);
      if (state?.question) setInput(state.question);
    })();
  }, [location.state, blueprintPrompt, loadSavedBlueprint, projectKey]);

  const handleSend = async () => {
    const question = input.trim();
    if (!question) return;

    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      // Build context from attached files
      let context = repoContext || "";
      if (attachedFiles.length > 0) {
        context += "\n\nAttached files:\n" + attachedFiles.map((f) => `--- ${f.name} (${f.type}) ---\n${f.content}`).join("\n\n");
      }
      const res = await askQuestion(
        question,
        context || undefined,
        activeRepoId ?? undefined,
        selectedModel,
      );
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.answer, tokens: res.tokens_used, model: res.model || selectedModel },
      ]);
      await saveContext(contextPageFor("workspace", projectKey), "last_ask_summary", res.answer.slice(0, 8000)).catch(() => {});
      await saveContext(contextPageFor("ask", projectKey), "repo_context", context).catch(() => {});
      await saveContext(contextPageFor("ask", projectKey), "last_question", question).catch(() => {});
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to get response.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleSendToPlan = async () => {
    const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant");
    const lastUser = [...messages].reverse().find((m) => m.role === "user");
    const summary = lastAssistant?.content || "";
    const question = lastUser?.content || input.trim();
    const desc = question
      ? `Based on this Ask triage:\n\n**Question:** ${question}\n\n**Answer:**\n${summary.slice(0, 4000)}`
      : summary.slice(0, 4000);
    await saveContext(contextPageFor("workspace", projectKey), "last_ask_summary", summary.slice(0, 8000)).catch(() => {});
    await saveContext(contextPageFor("plan", projectKey), "repo_context", repoContext).catch(() => {});
    await saveContext(contextPageFor("plan", projectKey), "project_description", desc).catch(() => {});
    navigate("/plan", { state: { projectDescription: desc, repoContext } });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex gap-4 h-[calc(100vh-8rem)]">
      {/* Conversation History Sidebar */}
      <ConversationHistory mode="ask" className="hidden lg:flex shrink-0" />

      <div className="flex-1 flex flex-col min-w-0">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <MessageSquare size={24} className="text-blue-600" />
            Ask Mode
          </h1>
          <p className="text-gray-500 mt-1">
            Ask any engineering question — architecture, debugging, code review, best practices.
          </p>
        </div>
        <ModelSelector value={selectedModel} onChange={setSelectedModel} compact />
      </div>

      {projectKey && (
        <div className="mb-2 text-xs text-slate-500" data-testid="ask-workspace-key">
          Active repo context: <span className="font-mono text-teal-700">{projectKey}</span>
        </div>
      )}

      <div className="mb-3">
        <div className="flex items-center justify-between gap-2 mb-1">
          <label className="block text-xs font-medium text-gray-600">Repo / Blueprint context</label>
          <div className="flex items-center gap-2">
            <button
              type="button"
              data-testid="ask-clear-context"
              onClick={() => {
                void (async () => {
                  setRepoContext("");
                  await clearBlueprintContext();
                  await clearContext("ask").catch(() => {});
                })();
              }}
              className="text-[11px] text-slate-500 hover:text-red-600 underline"
            >
              Clear context
            </button>
            <button
              type="button"
              data-testid="ask-reload-blueprint"
              onClick={() => {
                void (async () => {
                  const prompt = await loadBlueprintPrompt(false);
                  if (prompt) setRepoContext(prompt);
                })();
              }}
              className="text-[11px] text-teal-700 hover:text-teal-900 underline"
            >
              Reload from Lattice
            </button>
          </div>
        </div>
        <textarea
          data-testid="ask-repo-context"
          value={repoContext}
          onChange={(e) => setRepoContext(e.target.value)}
          placeholder="Blueprint or repo analysis loads here from Lattice / workspace…"
          className="w-full px-3 py-2 border border-gray-200 rounded-lg text-xs font-mono h-20 resize-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Context Files Bar */}
      <AttachedContextPanel
        files={attachedFiles}
        onChange={setAttachedFiles}
        accent="blue"
        className="mb-3"
      />

      {/* Prompt Hygiene Tips */}
      <PromptHygieneTips mode="ask" className="mb-3" />

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 bg-gray-50 rounded-xl p-4 mb-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            <Bot size={48} className="mb-3" />
            <p className="text-lg font-medium">Ask me anything</p>
            <p className="text-sm mt-1">
              Architecture decisions, code review, debugging help, best practices...
            </p>
            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-2 w-full max-w-lg">
              {[
                "How should I structure a microservices migration?",
                "What's the best way to handle auth in a React app?",
                "Review my API design for a claims processing system",
                "How do I set up CI/CD for a monorepo?",
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => setInput(suggestion)}
                  className="text-left text-xs bg-white border border-gray-200 rounded-lg p-3 hover:bg-blue-50 hover:border-blue-300 transition"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            {msg.role === "assistant" && (
              <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                <Bot size={16} className="text-blue-600" />
              </div>
            )}
            <div
              className={`max-w-[75%] rounded-xl p-4 ${
                msg.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-white border border-gray-200 text-gray-800"
              }`}
            >
                {msg.role === "assistant" ? (
                  <div className="space-y-3">
                    {msg.content.split(/(```[\s\S]*?```)/g).map((part, i) => {
                      if (part.startsWith("```")) {
                        const lines = part.slice(3, -3).split("\n");
                        const lang = lines[0]?.trim() || "text";
                        const code = lines.slice(1).join("\n");
                        return <CodeOutput key={i} code={code} language={lang} title={lang} maxHeight="300px" />;
                      }
                      return part ? <pre key={i} className="text-sm whitespace-pre-wrap font-sans">{part}</pre> : null;
                    })}
                    {/* Copy full response button */}
                    <button
                      onClick={async () => {
                        await navigator.clipboard.writeText(msg.content);
                        setCopiedMsgIdx(idx);
                        setTimeout(() => setCopiedMsgIdx(null), 2000);
                      }}
                      className={`mt-2 flex items-center gap-1 text-xs px-2 py-1 rounded transition ${
                        copiedMsgIdx === idx
                          ? "text-green-600 bg-green-50"
                          : "text-slate-400 hover:text-slate-600 hover:bg-slate-100"
                      }`}
                    >
                      {copiedMsgIdx === idx ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                      {copiedMsgIdx === idx ? "Copied!" : "Copy full response"}
                    </button>
                  </div>
                ) : (
                  <pre className="text-sm whitespace-pre-wrap font-sans">{msg.content}</pre>
                )}
              {(msg.tokens || msg.model) && (
                <p className="text-xs mt-2 opacity-60">
                  {msg.tokens ? `${msg.tokens} tokens` : ""}{msg.model ? ` • ${msg.model}` : ""}
                </p>
              )}
            </div>
            {msg.role === "user" && (
              <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0">
                <User size={16} className="text-gray-600" />
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
              <Bot size={16} className="text-blue-600" />
            </div>
            <div className="bg-white border border-gray-200 rounded-xl p-4">
              <Loader2 size={16} className="animate-spin text-blue-600" />
            </div>
          </div>
        )}
      </div>

      {/* Error */}
      <PhaseErrorBanner error={error} density="compact" />

      {/* Input */}
      <div className="flex gap-2 flex-wrap items-end">
        <textarea
          data-testid="ask-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question... (Enter to send, Shift+Enter for new line)"
          className="flex-1 min-w-[200px] px-4 py-3 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none h-12"
          rows={1}
        />
        {messages.some((m) => m.role === "assistant") && (
          <button
            type="button"
            data-testid="ask-send-to-plan"
            onClick={handleSendToPlan}
            className="px-3 py-3 border border-indigo-300 text-indigo-700 rounded-xl hover:bg-indigo-50 text-sm flex items-center gap-1"
          >
            Send to Plan <ArrowRight size={14} />
          </button>
        )}
        <button
          data-testid="ask-send"
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="px-4 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          <Send size={16} />
        </button>
      </div>
      </div>
    </div>
  );
}
