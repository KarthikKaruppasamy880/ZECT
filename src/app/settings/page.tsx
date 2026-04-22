"use client";

import { useState } from "react";
import Header from "@/components/layout/Header";
import Card from "@/components/shared/Card";

interface SettingToggle {
  id: string;
  label: string;
  description: string;
  enabled: boolean;
}

interface SettingOption {
  id: string;
  label: string;
  description: string;
  value: string;
  options: string[];
}

export default function SettingsPage() {
  const [toggles, setToggles] = useState<SettingToggle[]>([
    { id: "auto-review", label: "Automated Code Review", description: "Automatically run security and quality checks when a build phase completes.", enabled: true },
    { id: "token-tracking", label: "Token Usage Tracking", description: "Track AI token consumption across all projects and sessions.", enabled: true },
    { id: "deploy-gates", label: "Deployment Gate Enforcement", description: "Block deployments when critical review findings are unresolved.", enabled: true },
    { id: "risk-alerts", label: "Risk Alert Notifications", description: "Send Slack/email notifications when new risk alerts are detected.", enabled: false },
    { id: "auto-plan", label: "Auto-Generate Plan from Requirements", description: "Automatically generate architecture and API plans from approved requirements.", enabled: false },
    { id: "session-context", label: "Session Context Memory", description: "Persist context across AI sessions using ZEF context management.", enabled: true },
  ]);

  const [selects, setSelects] = useState<SettingOption[]>([
    { id: "default-stage", label: "Default Starting Stage", description: "Which stage new projects start in by default.", value: "Ask Mode", options: ["Ask Mode", "Plan Mode", "Build Phase"] },
    { id: "review-severity", label: "Minimum Review Severity", description: "Only surface findings at or above this severity level.", value: "Medium", options: ["Critical", "High", "Medium", "Low", "Info"] },
    { id: "deploy-approval", label: "Deployment Approval Mode", description: "Who must approve before a deployment can proceed.", value: "Tech Lead + PM", options: ["Anyone", "Tech Lead", "Tech Lead + PM", "VP Engineering"] },
    { id: "token-budget", label: "Monthly Token Budget Alert", description: "Alert threshold for monthly AI token consumption.", value: "80% of budget", options: ["50% of budget", "70% of budget", "80% of budget", "90% of budget", "No alert"] },
  ]);

  const handleToggle = (id: string) => {
    setToggles((prev) =>
      prev.map((t) => (t.id === id ? { ...t, enabled: !t.enabled } : t))
    );
  };

  const handleSelect = (id: string, value: string) => {
    setSelects((prev) =>
      prev.map((s) => (s.id === id ? { ...s, value } : s))
    );
  };

  return (
    <>
      <Header
        title="Platform Settings"
        subtitle="Configure ZECT behavior, workflow gates, notification preferences, and AI integration settings."
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: "Settings" },
        ]}
      />

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-8">
        {/* Feature Toggles */}
        <Card>
          <h3 className="text-lg font-semibold text-slate-900 mb-4">Feature Toggles</h3>
          <div className="space-y-4">
            {toggles.map((toggle) => (
              <div key={toggle.id} className="flex items-start justify-between gap-4 p-3 bg-slate-50 rounded-xl">
                <div className="min-w-0">
                  <div className="text-sm font-medium text-slate-800">{toggle.label}</div>
                  <div className="text-xs text-slate-500 mt-0.5">{toggle.description}</div>
                </div>
                <button
                  onClick={() => handleToggle(toggle.id)}
                  className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ${
                    toggle.enabled ? "bg-blue-600" : "bg-slate-300"
                  }`}
                >
                  <span
                    className={`pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transform transition-transform duration-200 ${
                      toggle.enabled ? "translate-x-5" : "translate-x-0"
                    }`}
                  />
                </button>
              </div>
            ))}
          </div>
        </Card>

        {/* Configuration Options */}
        <Card>
          <h3 className="text-lg font-semibold text-slate-900 mb-4">Configuration</h3>
          <div className="space-y-4">
            {selects.map((setting) => (
              <div key={setting.id} className="p-3 bg-slate-50 rounded-xl">
                <div className="text-sm font-medium text-slate-800">{setting.label}</div>
                <div className="text-xs text-slate-500 mt-0.5 mb-2">{setting.description}</div>
                <select
                  value={setting.value}
                  onChange={(e) => handleSelect(setting.id, e.target.value)}
                  className="w-full px-3 py-2 text-sm bg-white border border-slate-200 rounded-xl text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  {setting.options.map((opt) => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Integration Status */}
      <Card className="mb-8">
        <h3 className="text-lg font-semibold text-slate-900 mb-4">Integration Status</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
          {[
            { name: "GitHub", status: "Connected", statusColor: "text-emerald-600 bg-emerald-50", description: "Repository sync and CI/CD" },
            { name: "Slack", status: "Connected", statusColor: "text-emerald-600 bg-emerald-50", description: "Alert notifications" },
            { name: "AWS", status: "Connected", statusColor: "text-emerald-600 bg-emerald-50", description: "Infrastructure and deployment" },
            { name: "Jira", status: "Not Connected", statusColor: "text-slate-500 bg-slate-100", description: "Issue tracking" },
            { name: "Datadog", status: "Connected", statusColor: "text-emerald-600 bg-emerald-50", description: "Monitoring and observability" },
            { name: "PagerDuty", status: "Not Connected", statusColor: "text-slate-500 bg-slate-100", description: "Incident management" },
            { name: "Confluence", status: "Not Connected", statusColor: "text-slate-500 bg-slate-100", description: "Documentation sync" },
            { name: "SonarQube", status: "Connected", statusColor: "text-emerald-600 bg-emerald-50", description: "Code quality analysis" },
          ].map((integration) => (
            <div key={integration.name} className="p-3 bg-slate-50 rounded-xl">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-slate-800">{integration.name}</span>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${integration.statusColor}`}>
                  {integration.status}
                </span>
              </div>
              <div className="text-xs text-slate-500">{integration.description}</div>
            </div>
          ))}
        </div>
      </Card>

      {/* Team & Roles */}
      <Card>
        <h3 className="text-lg font-semibold text-slate-900 mb-4">Team Roles & Permissions</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left py-2 px-3 text-slate-500 font-medium">Team Member</th>
                <th className="text-left py-2 px-3 text-slate-500 font-medium">Role</th>
                <th className="text-left py-2 px-3 text-slate-500 font-medium">Permissions</th>
                <th className="text-left py-2 px-3 text-slate-500 font-medium">Last Active</th>
              </tr>
            </thead>
            <tbody>
              {[
                { name: "Sarah Chen", role: "Platform Lead", perms: "Admin — Full access", lastActive: "2 hours ago" },
                { name: "Marcus Johnson", role: "Senior Engineer", perms: "Write — Projects, builds, deploys", lastActive: "1 hour ago" },
                { name: "Priya Patel", role: "Frontend Lead", perms: "Write — Projects, builds", lastActive: "3 hours ago" },
                { name: "David Kim", role: "Backend Engineer", perms: "Write — Projects, builds", lastActive: "30 min ago" },
                { name: "Alex Kumar", role: "DevOps Engineer", perms: "Admin — Infra, deploys, settings", lastActive: "15 min ago" },
                { name: "Lisa Wong", role: "UI/UX Engineer", perms: "Write — Projects, reviews", lastActive: "4 hours ago" },
                { name: "Elena Rodriguez", role: "ML Engineer", perms: "Write — Projects, builds", lastActive: "1 day ago" },
                { name: "Raj Patel", role: "Data Scientist", perms: "Read — Projects, analytics", lastActive: "2 days ago" },
              ].map((member) => (
                <tr key={member.name} className="border-b border-slate-100 last:border-0">
                  <td className="py-2.5 px-3 font-medium text-slate-800">{member.name}</td>
                  <td className="py-2.5 px-3 text-slate-600">{member.role}</td>
                  <td className="py-2.5 px-3 text-slate-500">{member.perms}</td>
                  <td className="py-2.5 px-3 text-slate-400">{member.lastActive}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}
