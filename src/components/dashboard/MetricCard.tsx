import { Metric } from "@/types";
import Card from "@/components/shared/Card";

interface MetricCardProps {
  metric: Metric;
}

export default function MetricCard({ metric }: MetricCardProps) {
  const trendColor =
    metric.trendDirection === "up"
      ? "text-emerald-600"
      : metric.trendDirection === "down"
        ? "text-amber-600"
        : "text-slate-500";

  return (
    <Card>
      <div className="text-sm text-slate-500">{metric.label}</div>
      <div className="text-3xl font-bold mt-2 text-slate-900">
        {metric.value}
      </div>
      <div className={`text-sm mt-2 ${trendColor}`}>{metric.trend}</div>
    </Card>
  );
}
