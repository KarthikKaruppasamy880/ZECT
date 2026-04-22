interface ProgressBarProps {
  value: number;
  className?: string;
  showLabel?: boolean;
}

export default function ProgressBar({
  value,
  className = "",
  showLabel = true,
}: ProgressBarProps) {
  const clampedValue = Math.min(100, Math.max(0, value));

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-blue-600 rounded-full transition-all duration-300"
          style={{ width: `${clampedValue}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-xs font-medium text-slate-500 w-10 text-right">
          {clampedValue}%
        </span>
      )}
    </div>
  );
}
