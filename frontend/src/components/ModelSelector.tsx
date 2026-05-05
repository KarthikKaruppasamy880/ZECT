import { useState, useEffect } from "react";
import { Cpu, Zap, Crown, Gift } from "lucide-react";

interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  cost_per_1k_input: number;
  cost_per_1k_output: number;
  free: boolean;
  quality: string;
  speed: string;
}

const MODELS: ModelInfo[] = [
  // OpenAI
  { id: "gpt-4o-mini", name: "GPT-4o Mini", provider: "openai", cost_per_1k_input: 0.00015, cost_per_1k_output: 0.0006, free: false, quality: "high", speed: "fast" },
  { id: "gpt-4o", name: "GPT-4o", provider: "openai", cost_per_1k_input: 0.005, cost_per_1k_output: 0.015, free: false, quality: "best", speed: "medium" },
  { id: "gpt-3.5-turbo", name: "GPT-3.5 Turbo", provider: "openai", cost_per_1k_input: 0.0005, cost_per_1k_output: 0.0015, free: false, quality: "good", speed: "fastest" },
  // Free models via OpenRouter
  { id: "meta-llama/llama-3.1-8b-instruct:free", name: "Llama 3.1 8B (Free)", provider: "openrouter", cost_per_1k_input: 0, cost_per_1k_output: 0, free: true, quality: "good", speed: "fast" },
  { id: "mistralai/mistral-7b-instruct:free", name: "Mistral 7B (Free)", provider: "openrouter", cost_per_1k_input: 0, cost_per_1k_output: 0, free: true, quality: "good", speed: "fast" },
  { id: "google/gemma-2-9b-it:free", name: "Gemma 2 9B (Free)", provider: "openrouter", cost_per_1k_input: 0, cost_per_1k_output: 0, free: true, quality: "good", speed: "fast" },
  { id: "qwen/qwen-2.5-7b-instruct:free", name: "Qwen 2.5 7B (Free)", provider: "openrouter", cost_per_1k_input: 0, cost_per_1k_output: 0, free: true, quality: "good", speed: "fast" },
  // Anthropic via OpenRouter
  { id: "anthropic/claude-3.5-sonnet", name: "Claude 3.5 Sonnet", provider: "openrouter", cost_per_1k_input: 0.003, cost_per_1k_output: 0.015, free: false, quality: "best", speed: "medium" },
  { id: "anthropic/claude-3-haiku", name: "Claude 3 Haiku", provider: "openrouter", cost_per_1k_input: 0.00025, cost_per_1k_output: 0.00125, free: false, quality: "good", speed: "fastest" },
];

interface ModelSelectorProps {
  value: string;
  onChange: (modelId: string) => void;
  compact?: boolean;
}

export default function ModelSelector({ value, onChange, compact = false }: ModelSelectorProps) {
  const selectedModel = MODELS.find((m) => m.id === value) || MODELS[0];

  if (compact) {
    return (
      <div className="flex items-center gap-2">
        <Cpu className="h-3.5 w-3.5 text-slate-400" />
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="text-xs border border-slate-200 rounded-md px-2 py-1 bg-white text-slate-700 focus:ring-1 focus:ring-blue-400"
        >
          <optgroup label="OpenAI (Paid)">
            {MODELS.filter((m) => m.provider === "openai").map((m) => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
          </optgroup>
          <optgroup label="Free Models (OpenRouter)">
            {MODELS.filter((m) => m.free).map((m) => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
          </optgroup>
          <optgroup label="Anthropic (OpenRouter)">
            {MODELS.filter((m) => m.provider === "openrouter" && !m.free).map((m) => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
          </optgroup>
        </select>
        {selectedModel.free && (
          <span className="px-1.5 py-0.5 bg-green-100 text-green-700 rounded text-[10px] font-medium flex items-center gap-0.5">
            <Gift className="h-2.5 w-2.5" /> FREE
          </span>
        )}
      </div>
    );
  }

  return (
    <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
      <div className="flex items-center justify-between mb-2">
        <label className="text-xs font-medium text-slate-600 flex items-center gap-1.5">
          <Cpu className="h-3.5 w-3.5" /> Model Selection
        </label>
        {selectedModel.free ? (
          <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded-full text-[10px] font-medium flex items-center gap-0.5">
            <Gift className="h-3 w-3" /> FREE
          </span>
        ) : (
          <span className="text-[10px] text-slate-400">
            ${selectedModel.cost_per_1k_input}/1K in • ${selectedModel.cost_per_1k_output}/1K out
          </span>
        )}
      </div>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full text-sm border border-slate-300 rounded-md px-3 py-2 bg-white text-slate-700 focus:ring-2 focus:ring-blue-400 focus:border-blue-400"
      >
        <optgroup label="OpenAI (Paid — needs OPENAI_API_KEY)">
          {MODELS.filter((m) => m.provider === "openai").map((m) => (
            <option key={m.id} value={m.id}>
              {m.name} — {m.quality} quality, {m.speed}
            </option>
          ))}
        </optgroup>
        <optgroup label="Free Models (needs OPENROUTER_API_KEY)">
          {MODELS.filter((m) => m.free).map((m) => (
            <option key={m.id} value={m.id}>
              {m.name} — {m.quality} quality, {m.speed}
            </option>
          ))}
        </optgroup>
        <optgroup label="Anthropic (needs OPENROUTER_API_KEY)">
          {MODELS.filter((m) => m.provider === "openrouter" && !m.free).map((m) => (
            <option key={m.id} value={m.id}>
              {m.name} — {m.quality} quality, {m.speed}
            </option>
          ))}
        </optgroup>
      </select>
      <div className="flex items-center gap-3 mt-2 text-[10px] text-slate-400">
        <span className="flex items-center gap-0.5"><Crown className="h-3 w-3" /> {selectedModel.quality}</span>
        <span className="flex items-center gap-0.5"><Zap className="h-3 w-3" /> {selectedModel.speed}</span>
        <span>{selectedModel.provider}</span>
      </div>
    </div>
  );
}

export { MODELS };
export type { ModelInfo };
