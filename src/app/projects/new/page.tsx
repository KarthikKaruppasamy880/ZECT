"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Header from "@/components/layout/Header";
import Card from "@/components/shared/Card";

interface FormData {
  name: string;
  description: string;
  team: string;
  type: string;
}

const projectTypes = [
  { value: "fullstack", label: "Full-Stack Application", description: "Frontend + Backend + Database" },
  { value: "api", label: "API Service", description: "Backend API with data layer" },
  { value: "frontend", label: "Frontend Application", description: "UI-only with external APIs" },
  { value: "library", label: "Shared Library", description: "Reusable package or SDK" },
  { value: "migration", label: "Migration Project", description: "Legacy system modernization" },
  { value: "infra", label: "Infrastructure", description: "Platform or DevOps tooling" },
];

const teams = [
  "Platform Engineering",
  "Claims Engineering",
  "Product Engineering",
  "Underwriting Tech",
  "AI/ML Engineering",
  "DevOps",
];

export default function CreateProjectPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [form, setForm] = useState<FormData>({
    name: "",
    description: "",
    team: "",
    type: "",
  });

  const totalSteps = 3;

  const canProceed = () => {
    if (step === 1) return form.name.trim() !== "" && form.description.trim() !== "";
    if (step === 2) return form.team !== "" && form.type !== "";
    return true;
  };

  const handleCreate = () => {
    router.push("/projects");
  };

  return (
    <>
      <Header
        title="Create New Project"
        subtitle="Set up a new engineering project with the delivery pipeline."
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: "Projects", href: "/projects" },
          { label: "Create New" },
        ]}
      />

      <div className="max-w-2xl mx-auto">
        {/* Step indicator */}
        <div className="flex items-center gap-0 mb-8">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex items-center">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                  s < step
                    ? "bg-emerald-500 text-white"
                    : s === step
                      ? "bg-slate-900 text-white"
                      : "bg-slate-200 text-slate-500"
                }`}
              >
                {s < step ? (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                ) : (
                  s
                )}
              </div>
              {s < totalSteps && (
                <div className={`w-24 h-0.5 mx-2 ${s < step ? "bg-emerald-400" : "bg-slate-200"}`} />
              )}
            </div>
          ))}
        </div>

        {step === 1 && (
          <Card>
            <h3 className="text-lg font-semibold text-slate-900 mb-1">Project Details</h3>
            <p className="text-sm text-slate-500 mb-6">What are you building?</p>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Project Name
                </label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="e.g., Policy Admin Modernization"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Description
                </label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="Describe the project goal, scope, and key deliverables..."
                  rows={4}
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 resize-none"
                />
              </div>
            </div>
          </Card>
        )}

        {step === 2 && (
          <Card>
            <h3 className="text-lg font-semibold text-slate-900 mb-1">Team & Type</h3>
            <p className="text-sm text-slate-500 mb-6">Who is building this and what kind of project is it?</p>

            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Team
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {teams.map((team) => (
                    <button
                      key={team}
                      onClick={() => setForm({ ...form, team })}
                      className={`px-4 py-3 rounded-xl text-sm text-left transition-colors border ${
                        form.team === team
                          ? "bg-slate-900 text-white border-slate-900"
                          : "bg-white text-slate-700 border-slate-200 hover:border-slate-300"
                      }`}
                    >
                      {team}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Project Type
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {projectTypes.map((type) => (
                    <button
                      key={type.value}
                      onClick={() => setForm({ ...form, type: type.value })}
                      className={`px-4 py-3 rounded-xl text-left transition-colors border ${
                        form.type === type.value
                          ? "bg-slate-900 text-white border-slate-900"
                          : "bg-white text-slate-700 border-slate-200 hover:border-slate-300"
                      }`}
                    >
                      <div className="text-sm font-medium">{type.label}</div>
                      <div className={`text-xs mt-0.5 ${form.type === type.value ? "text-slate-300" : "text-slate-500"}`}>
                        {type.description}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </Card>
        )}

        {step === 3 && (
          <Card>
            <h3 className="text-lg font-semibold text-slate-900 mb-1">Review & Create</h3>
            <p className="text-sm text-slate-500 mb-6">Confirm your project details before starting the delivery pipeline.</p>

            <div className="space-y-4">
              <div className="bg-slate-50 rounded-xl p-4">
                <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Project Name</div>
                <div className="text-sm font-medium text-slate-900">{form.name}</div>
              </div>
              <div className="bg-slate-50 rounded-xl p-4">
                <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Description</div>
                <div className="text-sm text-slate-700">{form.description}</div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-50 rounded-xl p-4">
                  <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Team</div>
                  <div className="text-sm font-medium text-slate-900">{form.team}</div>
                </div>
                <div className="bg-slate-50 rounded-xl p-4">
                  <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Type</div>
                  <div className="text-sm font-medium text-slate-900">
                    {projectTypes.find((t) => t.value === form.type)?.label}
                  </div>
                </div>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mt-4">
                <div className="text-sm text-blue-800 font-medium mb-1">What happens next</div>
                <div className="text-xs text-blue-700">
                  Your project will start in <strong>Ask Mode</strong> where you define business goals, users, constraints, and dependencies before any implementation begins.
                </div>
              </div>
            </div>
          </Card>
        )}

        <div className="flex items-center justify-between mt-6">
          {step > 1 ? (
            <button
              onClick={() => setStep(step - 1)}
              className="px-5 py-2.5 rounded-xl text-sm font-medium text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 transition-colors"
            >
              Back
            </button>
          ) : (
            <div />
          )}
          {step < totalSteps ? (
            <button
              onClick={() => setStep(step + 1)}
              disabled={!canProceed()}
              className="px-5 py-2.5 rounded-xl text-sm font-medium text-white bg-slate-900 hover:bg-slate-800 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Continue
            </button>
          ) : (
            <button
              onClick={handleCreate}
              className="px-5 py-2.5 rounded-xl text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 transition-colors"
            >
              Create Project
            </button>
          )}
        </div>
      </div>
    </>
  );
}
