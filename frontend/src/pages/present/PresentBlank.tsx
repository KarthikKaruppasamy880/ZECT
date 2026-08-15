import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { encodeDeckId, mentrixPresentBlank } from "@/lib/api";

export default function PresentBlank() {
  const nav = useNavigate();
  const [status, setStatus] = useState("Creating blank deck…");

  useEffect(() => {
    mentrixPresentBlank()
      .then((out) => nav(`/present/d/${encodeDeckId(out.path)}`, { replace: true }))
      .catch((e) => setStatus(e instanceof Error ? e.message : "Blank deck failed"));
  }, [nav]);

  return (
    <p className="text-sm text-slate-600" data-testid="present-blank-page">
      {status}
    </p>
  );
}
