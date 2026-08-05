import { AlertCircle } from "lucide-react";

interface PhaseErrorBannerProps {
  error: string | null | undefined;
  className?: string;
  /** denser = rounded-lg + smaller icon (Ask); roomy = rounded-xl (Plan) */
  density?: "compact" | "roomy" | "plain";
  testId?: string;
}

/** Shared red error strip for Agent Workspace phase pages. */
export default function PhaseErrorBanner({
  error,
  className = "",
  density = "compact",
  testId,
}: PhaseErrorBannerProps) {
  if (!error) return null;

  if (density === "plain") {
    return (
      <div
        data-testid={testId}
        className={`bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm ${className}`}
        role="alert"
      >
        {error}
      </div>
    );
  }

  const shell =
    density === "roomy"
      ? "bg-red-50 border border-red-200 rounded-xl p-4 flex items-center gap-3"
      : "mb-3 bg-red-50 border border-red-200 rounded-lg p-3 flex items-center gap-2";
  const icon = density === "roomy" ? 18 : 16;

  return (
    <div data-testid={testId} className={`${shell} ${className}`} role="alert">
      <AlertCircle size={icon} className="text-red-500 shrink-0" />
      <span className="text-sm text-red-700">{error}</span>
    </div>
  );
}
