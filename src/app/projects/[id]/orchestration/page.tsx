"use client";

import { useParams } from "next/navigation";
import RepoCard from "@/components/orchestration/RepoCard";
import DependencyMap from "@/components/orchestration/DependencyMap";
import OrchestrationTimeline from "@/components/orchestration/OrchestrationTimeline";
import OrchestrationSummary from "@/components/orchestration/OrchestrationSummary";
import Card from "@/components/shared/Card";
import { getOrchestration } from "@/data/orchestration";

export default function ProjectOrchestrationPage() {
  const params = useParams();
  const projectId = params.id as string;
  const orchestration = getOrchestration(projectId);

  if (!orchestration) {
    return (
      <Card className="text-center py-12">
        <div className="text-slate-400 text-sm mb-2">
          No multi-repo orchestration configured for this project.
        </div>
        <p className="text-xs text-slate-400">
          Add repositories to this project to enable cross-repo dependency tracking,
          CI monitoring, and orchestration timeline.
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <OrchestrationSummary orchestration={orchestration} />

      <div>
        <h3 className="text-lg font-semibold text-slate-900 mb-3">Repositories</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {orchestration.repositories.map((repo) => (
            <RepoCard key={repo.id} repo={repo} />
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <DependencyMap
          repositories={orchestration.repositories}
          dependencies={orchestration.dependencies}
        />
        <OrchestrationTimeline
          events={orchestration.events}
          repositories={orchestration.repositories}
        />
      </div>
    </div>
  );
}
