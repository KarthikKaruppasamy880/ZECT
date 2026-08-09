import { useEffect, useState } from "react";
import { Cpu, Zap, Crown, Gift } from "lucide-react";
import { getMentrixLlmGateway } from "@/lib/api";

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

const CLOUD_MODELS: ModelInfo[] = [
  { id: "gpt-4o-mini", name: "GPT-4o Mini", provider: "openai", cost_per_1k_input: 0.00015, cost_per_1k_output: 0.0006, free: false, quality: "high", speed: "fast" },
  { id: "gpt-4o", name: "GPT-4o", provider: "openai", cost_per_1k_input: 0.005, cost_per_1k_output: 0.015, free: false, quality: "best", speed: "medium" },
  { id: "gpt-3.5-turbo", name: "GPT-3.5 Turbo", provider: "openai", cost_per_1k_input: 0.0005, cost_per_1k_output: 0.0015, free: false, quality: "good", speed: "fastest" },
  { id: "claude-3.5-sonnet", name: "Claude 3.5 Sonnet", provider: "anthropic", cost_per_1k_input: 0.003, cost_per_1k_output: 0.015, free: false, quality: "best", speed: "medium" },
  { id: "claude-3-haiku", name: "Claude 3 Haiku", provider: "anthropic", cost_per_1k_input: 0.00025, cost_per_1k_output: 0.00125, free: false, quality: "good", speed: "fastest" },
];

const MENTRIX_LOCAL_SEED: ModelInfo[] = [
  { id: "qwen2.5:7b", name: "Mentrix Local — Qwen 2.5 7B", provider: "mentrix_local", cost_per_1k_input: 0, cost_per_1k_output: 0, free: true, quality: "good", speed: "medium" },
  { id: "llama3.1", name: "Mentrix Local — Llama 3.1", provider: "mentrix_local", cost_per_1k_input: 0, cost_per_1k_output: 0, free: true, quality: "good", speed: "medium" },
  { id: "llama3.1:8b", name: "Mentrix Local — Llama 3.1 8B", provider: "mentrix_local", cost_per_1k_input: 0, cost_per_1k_output: 0, free: true, quality: "good", speed: "medium" },
];

interface ModelSelectorProps {
  value: string;
  onChange: (modelId: string) => void;
  compact?: boolean;
  showGatewayChip?: boolean;
}

export default function ModelSelector({
  value,
  onChange,
  compact = false,
  showGatewayChip = true,
}: ModelSelectorProps) {
  const [localModels, setLocalModels] = useState<ModelInfo[]>(MENTRIX_LOCAL_SEED);
  const [gatewayOnline, setGatewayOnline] = useState<boolean | null>(null);
  const [gatewayLabel, setGatewayLabel] = useState("Mentrix Local LLM");

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const g = await getMentrixLlmGateway();
        if (cancelled) return;
        setGatewayOnline(Boolean(g.online));
        setGatewayLabel(g.label || (g.online ? "Mentrix Local LLM online" : "Mentrix Local LLM offline"));
        if (g.models?.length) {
          const known = new Set(MENTRIX_LOCAL_SEED.map((m) => m.id));
          const extras = g.models
            .filter((id) => !known.has(id))
            .map(
              (id): ModelInfo => ({
                id,
                name: `Mentrix Local — ${id}`,
                provider: "mentrix_local",
                cost_per_1k_input: 0,
                cost_per_1k_output: 0,
                free: true,
                quality: "good",
                speed: "medium",
              }),
            );
          setLocalModels([...MENTRIX_LOCAL_SEED, ...extras]);
        }
      } catch {
        if (!cancelled) {
          setGatewayOnline(false);
          setGatewayLabel("Mentrix Local LLM offline");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const allModels = [...localModels, ...CLOUD_MODELS];
  const selectedModel = allModels.find((m) => m.id === value) || allModels[0];

  const chip =
    showGatewayChip && gatewayOnline !== null ? (
      <span
        data-testid="mentrix-local-llm-chip"
        className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
          gatewayOnline ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-500"
        }`}
        title={gatewayLabel}
      >
        {gatewayOnline ? "Mentrix Local LLM online" : "Mentrix Local LLM offline"}
      </span>
    ) : null;

  if (compact) {
    return (
      <div className="flex items-center gap-2 flex-wrap">
        <Cpu className="h-3.5 w-3.5 text-slate-400" />
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          data-testid="model-selector"
          className="text-xs border border-slate-200 rounded-md px-2 py-1 bg-white text-slate-700 focus:ring-1 focus:ring-blue-400"
        >
          <optgroup label="Mentrix Local">
            {localModels.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </optgroup>
          <optgroup label="OpenAI">
            {CLOUD_MODELS.filter((m) => m.provider === "openai").map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </optgroup>
          <optgroup label="Anthropic">
            {CLOUD_MODELS.filter((m) => m.provider === "anthropic").map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </optgroup>
        </select>
        {selectedModel.free && (
          <span className="px-1.5 py-0.5 bg-green-100 text-green-700 rounded text-[10px] font-medium flex items-center gap-0.5">
            <Gift className="h-2.5 w-2.5" /> FREE
          </span>
        )}
        {chip}
      </div>
    );
  }

  return (
    <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
      <div className="flex items-center justify-between mb-2 gap-2 flex-wrap">
        <label className="text-xs font-medium text-slate-600 flex items-center gap-1.5">
          <Cpu className="h-3.5 w-3.5" /> Model Selection
        </label>
        <div className="flex items-center gap-2">
          {chip}
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
      </div>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        data-testid="model-selector"
        className="w-full text-sm border border-slate-300 rounded-md px-3 py-2 bg-white text-slate-700 focus:ring-2 focus:ring-blue-400 focus:border-blue-400"
      >
        <optgroup label="Mentrix Local (ZECT_LLM_BASE_URL)">
          {localModels.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name} — {m.quality} quality, {m.speed}
            </option>
          ))}
        </optgroup>
        <optgroup label="OpenAI (needs OPENAI_API_KEY)">
          {CLOUD_MODELS.filter((m) => m.provider === "openai").map((m) => (
            <option key={m.id} value={m.id}>
              {m.name} — {m.quality} quality, {m.speed}
            </option>
          ))}
        </optgroup>
        <optgroup label="Anthropic (needs ANTHROPIC_API_KEY)">
          {CLOUD_MODELS.filter((m) => m.provider === "anthropic").map((m) => (
            <option key={m.id} value={m.id}>
              {m.name} — {m.quality} quality, {m.speed}
            </option>
          ))}
        </optgroup>
      </select>
      <div className="flex items-center gap-3 mt-2 text-[10px] text-slate-400">
        <span className="flex items-center gap-0.5">
          <Crown className="h-3 w-3" /> {selectedModel.quality}
        </span>
        <span className="flex items-center gap-0.5">
          <Zap className="h-3 w-3" /> {selectedModel.speed}
        </span>
        <span>{selectedModel.provider === "mentrix_local" ? "Mentrix Local" : selectedModel.provider}</span>
      </div>
    </div>
  );
}

export { CLOUD_MODELS as MODELS, MENTRIX_LOCAL_SEED };
export type { ModelInfo };
