import { useCallback, useEffect, useState } from "react";
import { useActiveProject } from "@/contexts/ActiveProjectContext";
import {
  contextPageFor,
  deriveProjectKey,
  readMentrixWorkspace,
  writeMentrixWorkspace,
  type MentrixWorkspace,
} from "@/lib/workspaceContext";
import {
  latticeBlueprintPrompt,
  latticeStatus,
  loadContext,
  saveContext,
  type LatticeStatusResponse,
} from "@/lib/api";

export function useWorkspaceRepoContext() {
  const { activeRepo, activeRepoId } = useActiveProject();
  const [workspace, setWorkspace] = useState<MentrixWorkspace | null>(() => readMentrixWorkspace());
  const [status, setStatus] = useState<LatticeStatusResponse | null>(null);
  const [blueprintPrompt, setBlueprintPrompt] = useState<string>("");
  const [loadingStatus, setLoadingStatus] = useState(false);

  const projectKey =
    activeRepo
      ? deriveProjectKey(activeRepo.owner, activeRepo.repo_name)
      : workspace?.projectKey || "";

  const localPath = activeRepo?.local_path || workspace?.path || "";

  const refreshStatus = useCallback(async (key?: string) => {
    const pk = key || projectKey;
    if (!pk) {
      setStatus(null);
      return null;
    }
    setLoadingStatus(true);
    try {
      const s = await latticeStatus(pk);
      setStatus(s);
      return s;
    } catch {
      setStatus({ indexed: false, project_key: pk, has_blueprint: false });
      return null;
    } finally {
      setLoadingStatus(false);
    }
  }, [projectKey]);

  const loadBlueprintPrompt = useCallback(async (rebuild = false) => {
    if (!projectKey) return "";
    try {
      const data = await latticeBlueprintPrompt(projectKey, localPath, rebuild);
      const prompt = (data.prompt || "").trim();
      if (!prompt) return "";
      setBlueprintPrompt(prompt);
      await saveContext(contextPageFor("workspace", projectKey), "blueprint_prompt", prompt).catch(() => {});
      return prompt;
    } catch {
      return "";
    }
  }, [projectKey, localPath]);

  const loadSavedBlueprint = useCallback(async () => {
    if (!projectKey) return "";
    try {
      const session = await loadContext(contextPageFor("workspace", projectKey), ["blueprint_prompt"]);
      const saved = session.entries.find((e) => e.key === "blueprint_prompt")?.value || "";
      setBlueprintPrompt(saved);
      return saved;
    } catch {
      return "";
    }
  }, [projectKey]);

  const clearBlueprintContext = useCallback(async () => {
    setBlueprintPrompt("");
    const page = contextPageFor("workspace", projectKey);
    await saveContext(page, "blueprint_prompt", "").catch(() => {});
    await saveContext(page, "repo_analysis", "").catch(() => {});
  }, [projectKey]);

  const syncFromActiveRepo = useCallback(() => {
    if (!activeRepo?.local_path) return;
    const pk = deriveProjectKey(activeRepo.owner, activeRepo.repo_name);
    writeMentrixWorkspace(activeRepo.local_path, pk);
    setWorkspace(readMentrixWorkspace());
  }, [activeRepo]);

  useEffect(() => {
    if (activeRepo?.local_path) {
      syncFromActiveRepo();
    }
  }, [activeRepo?.repo_id, activeRepo?.local_path, syncFromActiveRepo]);

  useEffect(() => {
    if (projectKey) {
      void refreshStatus(projectKey);
      void loadSavedBlueprint();
    }
  }, [projectKey, refreshStatus, loadSavedBlueprint]);

  return {
    activeRepo,
    activeRepoId,
    projectKey,
    localPath,
    workspace,
    latticeStatus: status,
    loadingStatus,
    blueprintPrompt,
    refreshStatus,
    loadBlueprintPrompt,
    loadSavedBlueprint,
    clearBlueprintContext,
    syncFromActiveRepo,
  };
}
