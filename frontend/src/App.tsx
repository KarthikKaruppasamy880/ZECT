import { useState, useEffect, lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "@/components/Layout";
import AgentWorkspaceShell from "@/components/AgentWorkspaceShell";
import ToastContainer from "@/components/Toast";
import Dashboard from "@/pages/Dashboard";
import Projects from "@/pages/Projects";
import ProjectDetail from "@/pages/ProjectDetail";
import CreateProject from "@/pages/CreateProject";
import PRViewer from "@/pages/PRViewer";
import Analytics from "@/pages/Analytics";
import Settings from "@/pages/Settings";
import Orchestration from "@/pages/Orchestration";
import Docs from "@/pages/Docs";
import RepoAnalysis from "@/pages/RepoAnalysis";
import BlueprintGenerator from "@/pages/BlueprintGenerator";
import DocGenerator from "@/pages/DocGenerator";
import AskMode from "@/pages/AskMode";
import PlanMode from "@/pages/PlanMode";
import TokenControls from "@/pages/TokenControls";
import AuditTrail from "@/pages/AuditTrail";
import RulesEngine from "@/pages/RulesEngine";
import Integrations from "@/pages/Integrations";
import ZectLearning from "@/pages/ZectLearning";
import PresentShell from "@/pages/present/PresentShell";
import PresentDashboard from "@/pages/present/PresentDashboard";
import PresentCreate from "@/pages/present/PresentCreate";
import PresentReview from "@/pages/present/PresentReview";
import PresentRehearse from "@/pages/present/PresentRehearse";
import PresentExport from "@/pages/present/PresentExport";
import PresentBlank from "@/pages/present/PresentBlank";
import PresentImport from "@/pages/present/PresentImport";
import PresentStudio from "@/pages/present/PresentStudio";
import PresentTemplatePreview from "@/pages/present/PresentTemplatePreview";
import ExportShare from "@/pages/ExportShare";
import OutputHistory from "@/pages/OutputHistory";
import AppRunner from "@/pages/AppRunner";
import FileExplorer from "@/pages/FileExplorer";
import GitOps from "@/pages/GitOps";
import CIMonitor from "@/pages/CIMonitor";
import MemoryDashboard from "@/pages/MemoryDashboard";
import MentrixNotes from "@/pages/MentrixNotes";
import DreamEngine from "@/pages/DreamEngine";
import DataLayer from "@/pages/DataLayer";
import DataFlywheel from "@/pages/DataFlywheel";
import Permissions from "@/pages/Permissions";
import SecurityIncidents from "@/pages/SecurityIncidents";
import MentrixFabric from "@/pages/MentrixFabric";
import ToolComparison from "@/pages/ToolComparison";
import TransferOnboarding from "@/pages/TransferOnboarding";
import SkillsEngine from "@/pages/SkillsEngine";
import FileOrganize from "@/pages/FileOrganize";
import KnowledgeBase from "@/pages/KnowledgeBase";
import Playbooks from "@/pages/Playbooks";
import ScheduledTasks from "@/pages/ScheduledTasks";
import SecretsManager from "@/pages/SecretsManager";
import CodeIndex from "@/pages/CodeIndex";
import SessionInsights from "@/pages/SessionInsights";
import Conversations from "@/pages/Conversations";
import RepoWorkspace from "@/pages/RepoWorkspace";
import DeveloperWorkspace from "@/pages/DeveloperWorkspace";
import AgentMode from "@/pages/AgentMode";
import LatticeGraph from "@/pages/LatticeGraph";
import Mentrix from "@/pages/Mentrix";
import MentrixCompanion from "@/pages/MentrixCompanion";
import MentrixSheets from "@/pages/MentrixSheets";
import MobileCompanion from "@/pages/MobileCompanion";
import SandboxGate from "@/pages/SandboxGate";
import WorkItems from "@/pages/WorkItems";
import ProjectIntelligencePage from "@/pages/ProjectIntelligence";
import SystemHealth from "@/pages/SystemHealth";
import Login from "@/pages/Login";
import { verifyToken, logout as apiLogout } from "@/lib/api";
import { ActiveProjectProvider } from "@/contexts/ActiveProjectContext";
import { SessionProvider } from "@/contexts/SessionContext";

/* Gap 5: Code-split heavy pages with React.lazy() */
const LazyCodeReview = lazy(() => import("@/pages/CodeReview"));
const LazyBuildPhase = lazy(() => import("@/pages/BuildPhase"));
const LazyReviewPhase = lazy(() => import("@/pages/ReviewPhase"));
const LazyDeployPhase = lazy(() => import("@/pages/DeployPhase"));

function PageLoader() {
  return (
    <div className="flex items-center justify-center h-64" role="status" aria-live="polite" data-testid="page-loader">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" aria-hidden />
      <span className="sr-only">Loading</span>
    </div>
  );
}

export default function App() {
  const [authenticated, setAuthenticated] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const token = localStorage.getItem("zect_token");
    if (!token) {
      setChecking(false);
      setAuthenticated(false);
      return;
    }
    const ac = new AbortController();
    const timer = window.setTimeout(() => ac.abort(), 8_000);
    verifyToken(token, { signal: ac.signal })
      .then(() => {
        if (!cancelled) setAuthenticated(true);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const aborted = err instanceof Error && err.name === "AbortError";
        if (aborted) {
          // Slow API must not trap the operator on an infinite loader.
          setAuthenticated(true);
          return;
        }
        localStorage.removeItem("zect_token");
        setAuthenticated(false);
      })
      .finally(() => {
        window.clearTimeout(timer);
        if (!cancelled) setChecking(false);
      });
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
      ac.abort();
    };
  }, []);

  const handleLogin = (token: string) => {
    localStorage.setItem("zect_token", token);
    setAuthenticated(true);
    // Desktop: land on Mentrix Companion Home after login
    if (typeof window !== "undefined" && window.zectDesktop?.isDesktopApp) {
      try {
        window.location.assign("/mentrix-home");
      } catch {
        /* ignore */
      }
    }
  };

  const handleLogout = () => {
    const token = localStorage.getItem("zect_token");
    if (token) {
      apiLogout(token).catch(() => {});
    }
    localStorage.removeItem("zect_token");
    localStorage.removeItem("zect_username");
    setAuthenticated(false);
  };

  if (checking) {
    return (
      <div
        className="min-h-screen bg-slate-900 flex items-center justify-center"
        role="status"
        aria-live="polite"
        aria-busy="true"
        data-testid="auth-checking"
      >
        <div className="text-white text-lg">Loading…</div>
      </div>
    );
  }

  if (!authenticated) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <ActiveProjectProvider>
    <SessionProvider>
    <BrowserRouter>
      <ToastContainer />
      <Routes>
        <Route element={<Layout onLogout={handleLogout} />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/projects/new" element={<CreateProject />} />
          <Route path="/projects/:id" element={<ProjectDetail />} />
          <Route path="/projects/:id/pr/:owner/:repo/:number" element={<PRViewer />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/orchestration" element={<Orchestration />} />
          <Route path="/repo-analysis" element={<RepoAnalysis />} />
          <Route path="/blueprint" element={<BlueprintGenerator />} />
          <Route path="/doc-generator" element={<DocGenerator />} />
          <Route element={<AgentWorkspaceShell />}>
            <Route path="/ask" element={<AskMode />} />
            <Route path="/plan" element={<PlanMode />} />
            <Route path="/build" element={<Suspense fallback={<PageLoader />}><LazyBuildPhase /></Suspense>} />
            <Route path="/review" element={<Suspense fallback={<PageLoader />}><LazyReviewPhase /></Suspense>} />
            <Route path="/deploy" element={<Suspense fallback={<PageLoader />}><LazyDeployPhase /></Suspense>} />
            <Route path="/mentrix" element={<Mentrix />} />
            <Route path="/agent-mode" element={<AgentMode />} />
          </Route>
          <Route path="/docs" element={<Docs />} />
          <Route path="/code-review" element={<Suspense fallback={<PageLoader />}><LazyCodeReview /></Suspense>} />
          <Route path="/token-controls" element={<TokenControls />} />
          <Route path="/audit-trail" element={<AuditTrail />} />
          <Route path="/rules" element={<RulesEngine />} />
          <Route path="/integrations" element={<Integrations />} />
          <Route path="/export" element={<ExportShare />} />
          <Route path="/output-history" element={<OutputHistory />} />
          <Route path="/app-runner" element={<AppRunner />} />
          <Route path="/file-explorer" element={<FileExplorer />} />
          <Route path="/git-ops" element={<GitOps />} />
          <Route path="/ci-monitor" element={<CIMonitor />} />
          <Route path="/memory" element={<MemoryDashboard />} />
          <Route path="/mentrix-notes" element={<MentrixNotes />} />
          <Route path="/dream-engine" element={<DreamEngine />} />
          <Route path="/data-layer" element={<DataLayer />} />
          <Route path="/data-flywheel" element={<DataFlywheel />} />
          <Route path="/permissions" element={<Permissions />} />
          <Route path="/security-incidents" element={<SecurityIncidents />} />
          <Route path="/fabric" element={<MentrixFabric />} />
          <Route path="/tool-comparison" element={<ToolComparison />} />
          <Route path="/transfer" element={<TransferOnboarding />} />
          <Route path="/skills-engine" element={<SkillsEngine />} />
          <Route path="/file-organize" element={<FileOrganize />} />
          <Route path="/knowledge-base" element={<KnowledgeBase />} />
          <Route path="/learning" element={<ZectLearning />} />
          <Route path="/present" element={<PresentShell />}>
            <Route index element={<PresentDashboard />} />
            <Route path="create" element={<PresentCreate />} />
            <Route path="blank" element={<PresentBlank />} />
            <Route path="import" element={<PresentImport />} />
            <Route path="templates" element={<PresentCreate />} />
            <Route path="templates/:templateId" element={<PresentTemplatePreview />} />
            <Route path="d/:deckId" element={<PresentReview />} />
            <Route path="d/:deckId/edit" element={<PresentStudio />} />
            <Route path="d/:deckId/rehearse" element={<PresentRehearse />} />
            <Route path="d/:deckId/export" element={<PresentExport />} />
          </Route>
          <Route path="/playbooks" element={<Playbooks />} />
          <Route path="/scheduled-tasks" element={<ScheduledTasks />} />
          <Route path="/secrets" element={<SecretsManager />} />
          <Route path="/code-index" element={<CodeIndex />} />
          <Route path="/session-insights" element={<SessionInsights />} />
          <Route path="/conversations" element={<Conversations />} />
          <Route path="/repo-workspace" element={<RepoWorkspace />} />
          <Route path="/workspace" element={<DeveloperWorkspace />} />
          <Route path="/lattice" element={<LatticeGraph />} />
          <Route path="/mentrix-home" element={<MentrixCompanion />} />
          <Route path="/sheets" element={<MentrixSheets />} />
          <Route path="/m/companion" element={<MobileCompanion />} />
          <Route path="/sandbox" element={<SandboxGate />} />
          <Route path="/work-items" element={<WorkItems />} />
          <Route path="/project-intelligence" element={<ProjectIntelligencePage />} />
          <Route path="/system-health" element={<SystemHealth />} />
        </Route>
      </Routes>
    </BrowserRouter>
    </SessionProvider>
    </ActiveProjectProvider>
  );
}
