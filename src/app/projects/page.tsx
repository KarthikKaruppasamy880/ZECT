"use client";

import { useState } from "react";
import Link from "next/link";
import Header from "@/components/layout/Header";
import ProjectCard from "@/components/dashboard/ProjectCard";
import Card from "@/components/shared/Card";
import { projects } from "@/data/projects";
import { ProjectStatus } from "@/types";

type FilterType = "all" | ProjectStatus;

export default function ProjectsPage() {
  const [filter, setFilter] = useState<FilterType>("all");
  const [search, setSearch] = useState("");

  const filtered = projects.filter((p) => {
    const matchesFilter = filter === "all" || p.status === filter;
    const matchesSearch =
      search === "" ||
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.team.toLowerCase().includes(search.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const filterOptions: { value: FilterType; label: string; count: number }[] = [
    { value: "all", label: "All", count: projects.length },
    {
      value: "active",
      label: "Active",
      count: projects.filter((p) => p.status === "active").length,
    },
    {
      value: "completed",
      label: "Completed",
      count: projects.filter((p) => p.status === "completed").length,
    },
    {
      value: "on-hold",
      label: "On Hold",
      count: projects.filter((p) => p.status === "on-hold").length,
    },
  ];

  return (
    <>
      <Header
        title="Projects"
        subtitle="All engineering projects tracked through the delivery pipeline."
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: "Projects" },
        ]}
        actions={
          <Link
            href="/projects/new"
            className="bg-slate-900 text-white px-5 py-3 rounded-2xl shadow hover:bg-slate-800 transition-colors text-sm font-medium"
          >
            Create New Project
          </Link>
        }
      />

      <Card className="mb-6">
        <div className="flex flex-col md:flex-row md:items-center gap-4">
          <div className="flex-1">
            <input
              type="text"
              placeholder="Search projects by name or team..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400"
            />
          </div>
          <div className="flex items-center gap-2">
            {filterOptions.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setFilter(opt.value)}
                className={`px-3 py-2 rounded-xl text-xs font-medium transition-colors ${
                  filter === opt.value
                    ? "bg-slate-900 text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {opt.label} ({opt.count})
              </button>
            ))}
          </div>
        </div>
      </Card>

      {filtered.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((project) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      ) : (
        <Card className="text-center py-12">
          <div className="text-slate-400 text-sm">
            No projects match your filters.
          </div>
        </Card>
      )}
    </>
  );
}
