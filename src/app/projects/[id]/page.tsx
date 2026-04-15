"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";
import { projects } from "@/data/projects";

export default function ProjectOverviewPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const project = projects.find((p) => p.id === projectId);

  useEffect(() => {
    if (project) {
      router.replace(`/projects/${project.id}/${project.currentStage}`);
    }
  }, [project, router]);

  return null;
}
