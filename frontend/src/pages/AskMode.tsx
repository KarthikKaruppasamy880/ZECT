import { useState } from "react";
import { askQuestion } from "@/lib/api";
import CodeOutput from "@/components/CodeOutput";
import ModelSelector from "@/components/ModelSelector";
import {
  MessageSquare,
  Send,
  Loader2,
  AlertCircle,
  Bot,
  User,
  Paperclip,
  Plus,
  X,
  FileText,
  FolderGit2,
  FileCode,
} from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
  tokens?: number;
  model?: string;
}

interface AttachedFile {
  id: string;
  name: string;
  type: "file" | "repo" | "snippet";
  content: string;
}

export default function AskMode() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [repoContext, setRepoContext] = useState("");
  const [selectedModel, setSelectedModel] = useState("gpt-4o-mini");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([]);
  const [showAddPanel, setShowAddPanel] = useState(false);
  const [newFileName, setNewFileName] = useState("");
  const [newFileContent, setNewFileContent] = useState("");
  const [newFileType, setNewFileType] = useState<"file" | "repo" | "snippet">("file");

  const handleAddFile = () => {
    if (!newFileName.trim() || !newFileContent.trim()) return;
    setAttachedFiles((prev) => [
      ...prev,
      { id: Date.now().toString(), name: newFileName.trim(), type: newFileType, content: newFileContent.trim() },
    ]);
    setNewFileName("");
    setNewFileContent("");
    setShowAddPanel(false);
  };

  const handleRemoveFile = (id: string) => {
    setAttachedFiles((prev) => prev.filter((f) => f.id !== id));
  };

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
      const res = await askQuestion(question, context || undefined);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.answer, tokens: res.tokens_used, model: res.model || selectedModel },
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

      {/* Context Files Bar */}
      <div className="mb-3 flex items-center gap-2 flex-wrap">
        <button
          onClick={() => setShowAddPanel(!showAddPanel)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition"
        >
          <Plus size={12} />
          Add files, repos, snippets
        </button>
        {attachedFiles.map((file) => (
          <div key={file.id} className="flex items-center gap-1 px-2 py-1 bg-slate-100 border border-slate-200 rounded-lg text-xs">
            {file.type === "file" && <FileText className="h-3 w-3 text-blue-500" />}
            {file.type === "repo" && <FolderGit2 className="h-3 w-3 text-green-500" />}
            {file.type === "snippet" && <FileCode className="h-3 w-3 text-purple-500" />}
            <span className="text-slate-700 max-w-[100px] truncate">{file.name}</span>
            <button onClick={() => handleRemoveFile(file.id)} className="text-slate-400 hover:text-red-500">
              <X className="h-3 w-3" />
            </button>
          </div>
        ))}
      </div>

      {/* Add File Panel */}
      {showAddPanel && (
        <div className="mb-3 p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
          <div className="flex gap-2">
            {(["file", "repo", "snippet"] as const).map((type) => (
              <button
                key={type}
                onClick={() => setNewFileType(type)}
                className={`px-3 py-1.5 text-xs rounded-lg font-medium transition flex items-center gap-1 ${
                  newFileType === type
                    ? "bg-blue-100 text-blue-700 border border-blue-300"
                    : "bg-white text-slate-600 border border-slate-200 hover:border-blue-300"
                }`}
              >
                {type === "file" && <FileText className="h-3 w-3" />}
                {type === "repo" && <FolderGit2 className="h-3 w-3" />}
                {type === "snippet" && <FileCode className="h-3 w-3" />}
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </button>
            ))}
          </div>
          <input
            type="text"
            value={newFileName}
            onChange={(e) => setNewFileName(e.target.value)}
            placeholder={newFileType === "file" ? "File path (e.g., src/utils/auth.ts)" : newFileType === "repo" ? "Repo URL or owner/repo" : "Snippet name"}
            className="w-full p-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500"
          />
          <textarea
            value={newFileContent}
            onChange={(e) => setNewFileContent(e.target.value)}
            placeholder="Paste file content, code snippet, or repo description here..."
            className="w-full h-24 p-2 border border-slate-300 rounded-lg text-xs font-mono focus:ring-2 focus:ring-blue-500 resize-none"
          />
          <div className="flex gap-2">
            <button onClick={handleAddFile} disabled={!newFileName.trim() || !newFileContent.trim()} className="px-3 py-1.5 bg-blue-600 text-white text-xs rounded-lg font-medium hover:bg-blue-700 disabled:bg-slate-300 transition">
              Add Context
            </button>
            <button onClick={() => setShowAddPanel(false)} className="px-3 py-1.5 bg-slate-200 text-slate-600 text-xs rounded-lg font-medium hover:bg-slate-300 transition">
              Cancel
            </button>
          </div>
        </div>
      )}

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
