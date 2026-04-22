"use client";

import { BuildTask } from "@/types";
import Card from "@/components/shared/Card";
import ProgressBar from "@/components/shared/ProgressBar";

interface BuildPhaseViewProps {
  tasks: BuildTask[];
}

const taskStatusStyles: Record<string, string> = {
  done: "bg-emerald-100 text-emerald-700",
  "in-progress": "bg-blue-100 text-blue-700",
  todo: "bg-slate-100 text-slate-500",
  blocked: "bg-red-100 text-red-700",
};

export default function BuildPhaseView({ tasks }: BuildPhaseViewProps) {
  const done = tasks.filter((t) => t.status === "done").length;
  const inProgress = tasks.filter((t) => t.status === "in-progress").length;
  const todo = tasks.filter((t) => t.status === "todo").length;
  const blocked = tasks.filter((t) => t.status === "blocked").length;
  const overallProgress =
    tasks.length > 0
      ? Math.round(tasks.reduce((sum, t) => sum + t.progress, 0) / tasks.length)
      : 0;

  return (
    <div className="space-y-6">
      <Card>
        <h3 className="text-lg font-semibold text-slate-900 mb-1">
          Build Progress
        </h3>
        <p className="text-sm text-slate-500 mb-4">
          Frontend shell, backend APIs, integrations, and documentation being
          built during this phase.
        </p>

        <div className="mb-4">
          <div className="flex justify-between text-sm mb-2">
            <span className="text-slate-600">Overall Progress</span>
            <span className="font-medium text-slate-900">{overallProgress}%</span>
          </div>
          <ProgressBar value={overallProgress} showLabel={false} />
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-emerald-50 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-emerald-700">{done}</div>
            <div className="text-xs text-slate-500 mt-1">Done</div>
          </div>
          <div className="bg-blue-50 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-blue-700">{inProgress}</div>
            <div className="text-xs text-slate-500 mt-1">In Progress</div>
          </div>
          <div className="bg-slate-50 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-slate-600">{todo}</div>
            <div className="text-xs text-slate-500 mt-1">To Do</div>
          </div>
          <div className="bg-red-50 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-red-700">{blocked}</div>
            <div className="text-xs text-slate-500 mt-1">Blocked</div>
          </div>
        </div>
      </Card>

      <Card>
        <h3 className="text-lg font-semibold text-slate-900 mb-4">Tasks</h3>
        <div className="space-y-3">
          {tasks.map((task) => (
            <div
              key={task.id}
              className="border border-slate-200 rounded-xl p-4 hover:border-slate-300 transition-colors"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                  <span className="font-medium text-sm text-slate-900">
                    {task.title}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded-full text-xs font-medium ${taskStatusStyles[task.status]}`}
                  >
                    {task.status === "in-progress"
                      ? "In Progress"
                      : task.status.charAt(0).toUpperCase() + task.status.slice(1)}
                  </span>
                </div>
                <span className="text-xs text-slate-500">{task.assignee}</span>
              </div>
              <ProgressBar value={task.progress} />
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
