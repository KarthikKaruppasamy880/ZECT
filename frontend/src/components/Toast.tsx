import { useEffect, useState, useCallback } from "react";
import { X, AlertCircle, CheckCircle, Info } from "lucide-react";

export interface ToastMessage {
  id: number;
  type: "error" | "success" | "info";
  message: string;
}

let toastId = 0;
let addToastFn: ((msg: Omit<ToastMessage, "id">) => void) | null = null;

/** Call from anywhere to show a toast. */
export function showToast(type: ToastMessage["type"], message: string) {
  addToastFn?.({ type, message });
}

export default function ToastContainer() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = useCallback((msg: Omit<ToastMessage, "id">) => {
    const id = ++toastId;
    setToasts((prev) => [...prev, { ...msg, id }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 5000);
  }, []);

  useEffect(() => {
    addToastFn = addToast;
    return () => { addToastFn = null; };
  }, [addToast]);

  const dismiss = (id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
      {toasts.map((t) => {
        const styles =
          t.type === "error"
            ? "bg-red-50 border-red-300 text-red-800"
            : t.type === "success"
            ? "bg-green-50 border-green-300 text-green-800"
            : "bg-blue-50 border-blue-300 text-blue-800";
        const Icon =
          t.type === "error" ? AlertCircle : t.type === "success" ? CheckCircle : Info;
        return (
          <div
            key={t.id}
            className={`flex items-start gap-2 px-4 py-3 rounded-lg border shadow-lg animate-in slide-in-from-right ${styles}`}
          >
            <Icon className="h-4 w-4 mt-0.5 flex-shrink-0" />
            <p className="text-sm flex-1">{t.message}</p>
            <button onClick={() => dismiss(t.id)} className="p-0.5 rounded hover:bg-black/10">
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
