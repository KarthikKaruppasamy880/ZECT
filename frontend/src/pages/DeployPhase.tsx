import { useState } from "react";
import { deployChecklist, deployRunbook, deployTriggerWorkflow, approvePermissionAudit } from "@/lib/api";
import CodeOutput from "@/components/CodeOutput";
import PhaseErrorBanner from "@/components/PhaseErrorBanner";
import { Rocket, Play, Loader2, CheckSquare, FileText, AlertCircle, Zap, ShieldAlert } from "lucide-react";

export default function DeployPhase() {
  const [projectName, setProjectName] = useState("");
  const [techStack, setTechStack] = useState("");
  const [environment, setEnvironment] = useState("production");
  const [deployType, setDeployType] = useState("standard");
  const [infrastructure, setInfrastructure] = useState("AWS");
  const [tab, setTab] = useState<"checklist" | "runbook">("checklist");
  const [loading, setLoading] = useState(false);
  const [checklistResult, setChecklistResult] = useState<any>(null);
  const [runbookResult, setRunbookResult] = useState<any>(null);
  const [error, setError] = useState("");

  // Trigger Deployment — actually fires a GitHub Actions run, gated by the
  // deploy_.* permission rule (require_approval by default).
  const [triggerOwner, setTriggerOwner] = useState("");
  const [triggerRepo, setTriggerRepo] = useState("");
  const [triggerWorkflowFile, setTriggerWorkflowFile] = useState("deploy.yml");
  const [triggerRef, setTriggerRef] = useState("main");
  const [triggerConfirmArmed, setTriggerConfirmArmed] = useState(false);
  const [triggerLoading, setTriggerLoading] = useState(false);
  const [triggerStatus, setTriggerStatus] = useState<{ status: string; audit_id: number | null; message: string } | null>(null);
  const [triggerError, setTriggerError] = useState("");

  const runTrigger = async (auditId?: number) => {
    setTriggerLoading(true);
    setTriggerError("");
    try {
      const res = await deployTriggerWorkflow(triggerOwner, triggerRepo, triggerWorkflowFile, triggerRef, environment, undefined, auditId);
      setTriggerStatus(res);
    } catch (e: any) {
      setTriggerError(e.message || "Failed to trigger deployment");
    } finally {
      setTriggerLoading(false);
      setTriggerConfirmArmed(false);
    }
  };

  const handleTriggerClick = () => {
    if (!triggerOwner.trim() || !triggerRepo.trim() || !triggerWorkflowFile.trim()) return;
    if (!triggerConfirmArmed) {
      setTriggerConfirmArmed(true);
      return;
    }
    runTrigger();
  };

  const handleApproveAndRetry = async () => {
    if (!triggerStatus?.audit_id) return;
    setTriggerLoading(true);
    setTriggerError("");
    try {
      await approvePermissionAudit(triggerStatus.audit_id, true, "Approved from Deploy Phase UI");
      await runTrigger(triggerStatus.audit_id);
    } catch (e: any) {
      setTriggerError(e.message || "Approval failed — you may need admin/lead permissions");
      setTriggerLoading(false);
    }
  };

  const handleGenerate = async () => {
    if (!projectName.trim()) return;
    setLoading(true);
    setError("");
    try {
      if (tab === "checklist") {
        const res = await deployChecklist(projectName, techStack || undefined, environment, deployType);
        setChecklistResult(res);
      } else {
        const res = await deployRunbook(projectName, techStack || undefined, infrastructure);
        setRunbookResult(res);
      }
    } catch (e: any) {
      setError(e.message || "Failed to generate");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-3 bg-green-100 rounded-xl">
          <Rocket className="h-6 w-6 text-green-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Deployment Phase</h1>
          <p className="text-slate-500">Generate deployment checklists, runbooks, and rollback plans</p>
        </div>
      </div>

      {/* Tab Selector */}
      <div className="flex gap-2 bg-slate-100 p-1 rounded-lg w-fit">
        <button
          onClick={() => setTab("checklist")}
          className={`px-4 py-2 rounded-md text-sm font-medium transition ${tab === "checklist" ? "bg-white shadow text-slate-900" : "text-slate-600 hover:text-slate-900"}`}
        >
          <CheckSquare className="inline h-4 w-4 mr-1" /> Checklist
        </button>
        <button
          onClick={() => setTab("runbook")}
          className={`px-4 py-2 rounded-md text-sm font-medium transition ${tab === "runbook" ? "bg-white shadow text-slate-900" : "text-slate-600 hover:text-slate-900"}`}
        >
          <FileText className="inline h-4 w-4 mr-1" /> Runbook
        </button>
      </div>

      {/* Input Form */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Project Name *</label>
            <input
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="e.g., Policy Admin Modernization"
              className="w-full p-2.5 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Tech Stack</label>
            <input
              type="text"
              value={techStack}
              onChange={(e) => setTechStack(e.target.value)}
              placeholder="e.g., React, Node.js, PostgreSQL, Docker"
              className="w-full p-2.5 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Environment</label>
            <select value={environment} onChange={(e) => setEnvironment(e.target.value)} className="w-full p-2 border border-slate-300 rounded-lg text-sm">
              <option value="staging">Staging</option>
              <option value="production">Production</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Deployment Type</label>
            <select value={deployType} onChange={(e) => setDeployType(e.target.value)} className="w-full p-2 border border-slate-300 rounded-lg text-sm">
              <option value="standard">Standard</option>
              <option value="canary">Canary</option>
              <option value="blue-green">Blue/Green</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Infrastructure</label>
            <select value={infrastructure} onChange={(e) => setInfrastructure(e.target.value)} className="w-full p-2 border border-slate-300 rounded-lg text-sm">
              <option value="AWS">AWS (EC2/ECS)</option>
              <option value="GCP">Google Cloud</option>
              <option value="Azure">Azure</option>
              <option value="on-prem">On-Premises</option>
            </select>
          </div>
        </div>

        <button
          onClick={handleGenerate}
          disabled={loading || !projectName.trim()}
          className="flex items-center gap-2 px-5 py-2.5 bg-green-600 hover:bg-green-700 disabled:bg-slate-300 text-white rounded-lg font-medium transition"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          {loading ? "Generating..." : `Generate ${tab === "checklist" ? "Checklist" : "Runbook"}`}
        </button>
      </div>

      <PhaseErrorBanner error={error} density="plain" />

      {/* Trigger Deployment — real GitHub Actions dispatch, not advice text */}
      <div className="bg-white rounded-xl border border-amber-200 shadow-sm p-5 space-y-4">
        <div className="flex items-center gap-2">
          <Zap className="h-5 w-5 text-amber-600" />
          <h3 className="font-semibold text-slate-900">Trigger Deployment</h3>
          <span className="text-xs text-slate-500">Fires a real GitHub Actions run — not a suggestion</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <input
            type="text"
            value={triggerOwner}
            onChange={(e) => { setTriggerOwner(e.target.value); setTriggerConfirmArmed(false); }}
            placeholder="GitHub owner/org"
            className="p-2 border border-slate-300 rounded-lg text-sm"
          />
          <input
            type="text"
            value={triggerRepo}
            onChange={(e) => { setTriggerRepo(e.target.value); setTriggerConfirmArmed(false); }}
            placeholder="Repo name"
            className="p-2 border border-slate-300 rounded-lg text-sm"
          />
          <input
            type="text"
            value={triggerWorkflowFile}
            onChange={(e) => { setTriggerWorkflowFile(e.target.value); setTriggerConfirmArmed(false); }}
            placeholder="Workflow file (deploy.yml)"
            className="p-2 border border-slate-300 rounded-lg text-sm"
          />
          <input
            type="text"
            value={triggerRef}
            onChange={(e) => { setTriggerRef(e.target.value); setTriggerConfirmArmed(false); }}
            placeholder="Branch/ref"
            className="p-2 border border-slate-300 rounded-lg text-sm"
          />
        </div>

        <button
          onClick={handleTriggerClick}
          disabled={triggerLoading || !triggerOwner.trim() || !triggerRepo.trim() || !triggerWorkflowFile.trim()}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-lg font-medium transition text-white disabled:bg-slate-300 ${
            triggerConfirmArmed ? "bg-red-600 hover:bg-red-700" : "bg-amber-600 hover:bg-amber-700"
          }`}
        >
          {triggerLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
          {triggerLoading
            ? "Triggering..."
            : triggerConfirmArmed
              ? `Confirm: run ${triggerWorkflowFile} on ${triggerRef} for real`
              : "Trigger Deployment"}
        </button>

        {triggerError && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-sm">{triggerError}</div>
        )}

        {triggerStatus?.status === "pending_approval" && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 space-y-2">
            <div className="flex items-center gap-2 text-amber-800 text-sm">
              <ShieldAlert className="h-4 w-4" />
              {triggerStatus.message}
            </div>
            <button
              onClick={handleApproveAndRetry}
              disabled={triggerLoading}
              className="px-4 py-2 bg-amber-600 hover:bg-amber-700 disabled:bg-slate-300 text-white rounded-lg text-sm font-medium"
            >
              Approve &amp; run now
            </button>
          </div>
        )}

        {triggerStatus?.status === "dispatched" && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-green-700 text-sm">
            {triggerStatus.message}
          </div>
        )}
      </div>

      {/* Checklist Result */}
      {tab === "checklist" && checklistResult && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
            <div className="p-4 border-b border-slate-200">
              <h3 className="font-semibold text-slate-900">Deployment Checklist ({checklistResult.checklist?.length || 0} items)</h3>
            </div>
            <div className="divide-y divide-slate-100">
              {checklistResult.checklist?.map((item: any, i: number) => (
                <div key={i} className="p-3 flex items-center gap-3">
                  <input type="checkbox" className="h-4 w-4 rounded border-slate-300 text-green-600" />
                  <span className={`px-1.5 py-0.5 text-[10px] rounded font-medium ${
                    item.category === "pre-deploy" ? "bg-blue-100 text-blue-700" :
                    item.category === "deploy" ? "bg-amber-100 text-amber-700" :
                    item.category === "post-deploy" ? "bg-green-100 text-green-700" :
                    "bg-slate-100 text-slate-700"
                  }`}>
                    {item.category}
                  </span>
                  <span className="flex-1 text-sm text-slate-700">{item.task}</span>
                  {item.critical && <AlertCircle className="h-4 w-4 text-red-500" />}
                  {item.automated && <span className="text-[10px] bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded">Auto</span>}
                </div>
              ))}
            </div>
          </div>

          {checklistResult.runbook && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
              <h3 className="font-semibold text-slate-900 mb-2">Runbook Summary</h3>
              <CodeOutput code={checklistResult.runbook} language="markdown" title="Deployment Runbook" maxHeight="300px" />
            </div>
          )}

          {checklistResult.rollback_plan && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
              <h3 className="font-semibold text-slate-900 mb-2">Rollback Plan</h3>
              <CodeOutput code={checklistResult.rollback_plan} language="markdown" title="Rollback Procedure" maxHeight="300px" />
            </div>
          )}
        </div>
      )}

      {/* Runbook Result */}
      {tab === "runbook" && runbookResult && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
            <div className="flex items-center gap-4 mb-4">
              <div className="px-3 py-1 bg-slate-100 rounded text-sm">
                Downtime: <strong>{runbookResult.estimated_downtime}</strong>
              </div>
              <div className={`px-3 py-1 rounded text-sm ${
                runbookResult.risk_level === "low" ? "bg-green-100 text-green-700" :
                runbookResult.risk_level === "medium" ? "bg-yellow-100 text-yellow-700" :
                "bg-red-100 text-red-700"
              }`}>
                Risk: <strong>{runbookResult.risk_level}</strong>
              </div>
            </div>
            <CodeOutput code={runbookResult.runbook} language="markdown" title="Full Deployment Runbook" maxHeight="500px" />
          </div>
        </div>
      )}
    </div>
  );
}
