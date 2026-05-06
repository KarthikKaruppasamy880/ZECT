import { useState, useEffect, lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "@/components/Layout";
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
import StagePage from "@/pages/StagePage";
import RepoAnalysis from "@/pages/RepoAnalysis";
import BlueprintGenerator from "@/pages/BlueprintGenerator";
import DocGenerator from "@/pages/DocGenerator";
import AskMode from "@/pages/AskMode";
import PlanMode from "@/pages/PlanMode";
import TokenControls from "@/pages/TokenControls";
import AuditTrail from "@/pages/AuditTrail";
import RulesEngine from "@/pages/RulesEngine";
import Integrations from "@/pages/Integrations";
import ExportShare from "@/pages/ExportShare";
import OutputHistory from "@/pages/OutputHistory";
import AppRunner from "@/pages/AppRunner";
import FileExplorer from "@/pages/FileExplorer";
import GitOps from "@/pages/GitOps";
import CIMonitor from "@/pages/CIMonitor";
import MemoryDashboard from "@/pages/MemoryDashboard";
import DreamEngine from "@/pages/DreamEngine";
import DataLayer from "@/pages/DataLayer";
import DataFlywheel from "@/pages/DataFlywheel";
import Permissions from "@/pages/Permissions";
import TransferOnboarding from "@/pages/TransferOnboarding";
import SkillsEngine from "@/pages/SkillsEngine";
import Login from "@/pages/Login";
import { verifyToken, logout as apiLogout } from "@/lib/api";

/* Gap 5: Code-split heavy pages with React.lazy() */
const LazyCodeReview = lazy(() => import("@/pages/CodeReview"));
const LazyBuildPhase = lazy(() => import("@/pages/BuildPhase"));
const LazyReviewPhase = lazy(() => import("@/pages/ReviewPhase"));
const LazyDeployPhase = lazy(() => import("@/pages/DeployPhase"));
const LazySkillLibrary = lazy(() => import("@/pages/SkillLibrary"));

function PageLoader() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
    </div>
  );
}

export default function App() {
  const [authenticated, setAuthenticated] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("zect_token");
    if (token) {
      verifyToken(token)
        .then(() => setAuthenticated(true))
        .catch(() => {
          localStorage.removeItem("zect_token");
          setAuthenticated(false);
        })
        .finally(() => setChecking(false));
    } else {
      setChecking(false);
    }
  }, []);

  const handleLogin = (token: string) => {
    localStorage.setItem("zect_token", token);
    setAuthenticated(true);
  };

  const handleLogout = () => {
    const token = localStorage.getItem("zect_token");
    if (token) {
      apiLogout(token).catch(() => {});
    }
    localStorage.removeItem("zect_token");
    setAuthenticated(false);
  };

  if (checking) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-white text-lg">Loading...</div>
      </div>
    );
  }

  if (!authenticated) {
    return <Login onLogin={handleLogin} />;
  }

  return (
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
          <Route path="/ask" element={<AskMode />} />
          <Route path="/plan" element={<PlanMode />} />
          <Route path="/docs" element={<Docs />} />
          <Route path="/code-review" element={<Suspense fallback={<PageLoader />}><LazyCodeReview /></Suspense>} />
          <Route path="/build" element={<Suspense fallback={<PageLoader />}><LazyBuildPhase /></Suspense>} />
          <Route path="/review" element={<Suspense fallback={<PageLoader />}><LazyReviewPhase /></Suspense>} />
          <Route path="/deploy" element={<Suspense fallback={<PageLoader />}><LazyDeployPhase /></Suspense>} />
          <Route path="/skills" element={<Suspense fallback={<PageLoader />}><LazySkillLibrary /></Suspense>} />
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
          <Route path="/dream-engine" element={<DreamEngine />} />
          <Route path="/data-layer" element={<DataLayer />} />
          <Route path="/data-flywheel" element={<DataFlywheel />} />
          <Route path="/permissions" element={<Permissions />} />
          <Route path="/transfer" element={<TransferOnboarding />} />
          <Route path="/skills-engine" element={<SkillsEngine />} />
          <Route path="/stages/:stage" element={<StagePage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
