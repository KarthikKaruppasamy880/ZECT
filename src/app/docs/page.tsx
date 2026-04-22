"use client";

import { useState } from "react";
import Header from "@/components/layout/Header";
import Card from "@/components/shared/Card";
import { docsItems } from "@/data/dashboard";

export default function DocsPage() {
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");

  const categories = ["all", ...Array.from(new Set(docsItems.map((d) => d.category)))];

  const filtered = docsItems.filter((doc) => {
    const matchesSearch =
      search === "" ||
      doc.title.toLowerCase().includes(search.toLowerCase()) ||
      doc.description.toLowerCase().includes(search.toLowerCase());
    const matchesCategory =
      selectedCategory === "all" || doc.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <>
      <Header
        title="Docs Center"
        subtitle="Standards, playbooks, and reference documentation for Zinnia engineering."
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: "Docs Center" },
        ]}
      />

      <Card className="mb-6">
        <div className="flex flex-col md:flex-row md:items-center gap-4">
          <div className="flex-1">
            <input
              type="text"
              placeholder="Search documentation..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400"
            />
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-3 py-2 rounded-xl text-xs font-medium transition-colors ${
                  selectedCategory === cat
                    ? "bg-slate-900 text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {cat === "all" ? "All" : cat}
              </button>
            ))}
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map((doc) => (
          <Card
            key={doc.id}
            className="hover:shadow-md hover:border-slate-300 transition-all cursor-pointer"
          >
            <div className="flex items-start justify-between mb-2">
              <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-600">
                {doc.category}
              </span>
              <span className="text-xs text-slate-400">{doc.lastUpdated}</span>
            </div>
            <h3 className="font-semibold text-slate-900 text-sm mb-2">
              {doc.title}
            </h3>
            <p className="text-xs text-slate-600 line-clamp-3">
              {doc.description}
            </p>
          </Card>
        ))}
      </div>

      {filtered.length === 0 && (
        <Card className="text-center py-12">
          <div className="text-slate-400 text-sm">
            No documents match your search.
          </div>
        </Card>
      )}
    </>
  );
}
