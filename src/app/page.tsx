import Link from "next/link";
import Header from "@/components/layout/Header";
import MetricCard from "@/components/dashboard/MetricCard";
import ProjectCard from "@/components/dashboard/ProjectCard";
import RecentActivity from "@/components/dashboard/RecentActivity";
import { projects } from "@/data/projects";
import { dashboardMetrics, recentActivity } from "@/data/dashboard";

export default function DashboardPage() {
  const activeProjects = projects.filter((p) => p.status === "active");

  return (
    <>
      <Header
        title="Engineering Delivery Control Tower"
        subtitle="Standardizes how Zinnia teams use AI: ask first, plan first, build in phases, validate with review, and prepare deployment early."
        actions={
          <Link
            href="/projects/new"
            className="bg-slate-900 text-white px-5 py-3 rounded-2xl shadow hover:bg-slate-800 transition-colors text-sm font-medium whitespace-nowrap"
          >
            Create New Project
          </Link>
        }
      />

      <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5 mb-8">
        {dashboardMetrics.map((metric) => (
          <MetricCard key={metric.label} metric={metric} />
        ))}
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-8">
        <div className="xl:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-slate-900">
              Active Projects
            </h3>
            <Link
              href="/projects"
              className="text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              View all
            </Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {activeProjects.slice(0, 4).map((project) => (
              <ProjectCard key={project.id} project={project} />
            ))}
          </div>
        </div>
        <div>
          <RecentActivity activities={recentActivity} />
        </div>
      </section>

      <section className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-slate-900">
            Why This Helps Zinnia
          </h3>
        </div>
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">
          {[
            "Reduces wasted context and token usage across AI sessions",
            "Prevents coding before requirements and architecture are clear",
            "Standardizes AI usage across all engineering teams",
            "Improves review quality through automated checks",
            "Improves deployment success with early readiness validation",
            "Enables leadership visibility into engineering delivery pipeline",
          ].map((item, i) => (
            <div
              key={i}
              className="p-3 bg-slate-50 rounded-xl text-sm text-slate-700"
            >
              {item}
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
