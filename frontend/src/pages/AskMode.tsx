import { useState } from "react";
import { askQuestion } from "@/lib/api";
import CodeOutput from "@/components/CodeOutput";
import {
  MessageSquare,
  Send,
  Loader2,
  AlertCircle,
  Bot,
  User,
  Zap,
} from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
  tokens?: number;
}

export default function AskMode() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [repoContext, setRepoContext] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showContext, setShowContext] = useState(false);

  const handleSend = async () => {
    const question = input.trim();
    if (!question) return;

    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const res = await askQuestion(question, repoContext || undefined);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.answer, tokens: res.tokens_used },
      ]);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to get response.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      {/* Header */}
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <MessageSquare size={24} className="text-blue-600" />
          Ask Mode
        </h1>
        <p className="text-gray-500 mt-1">
          Ask any engineering question — architecture, debugging, code review, best practices.
          Powered by OpenAI GPT-4o-mini.
        </p>
      </div>

      {/* Repo Context Toggle */}
      <div className="mb-3">
        <button
          onClick={() => setShowContext(!showContext)}
          className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
        >
          <Zap size={14} />
          {showContext ? "Hide" : "Add"} repo context for smarter answers
        </button>
        {showContext && (
          <textarea
            value={repoContext}
            onChange={(e) => setRepoContext(e.target.value)}
            placeholder="Paste repo analysis output, README content, or architecture notes here to give the AI context about your project..."
            className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 h-24 resize-none"
          />
        )}
      </div>

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
                </div>
              ) : (
                <pre className="text-sm whitespace-pre-wrap font-sans">{msg.content}</pre>
              )}
              {msg.tokens && (
                <p className="text-xs mt-2 opacity-60">{msg.tokens} tokens used</p>
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
      {error && (
        <div className="mb-3 bg-red-50 border border-red-200 rounded-lg p-3 flex items-center gap-2">
          <AlertCircle size={16} className="text-red-500" />
          <span className="text-sm text-red-700">{error}</span>
        </div>
      )}

      {/* Input */}
      <div className="flex gap-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question... (Enter to send, Shift+Enter for new line)"
          className="flex-1 px-4 py-3 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none h-12"
          rows={1}
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="px-4 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  );
}
