import { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "@/components/Layout";
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
import CodeReview from "@/pages/CodeReview";
import BuildPhase from "@/pages/BuildPhase";
import ReviewPhase from "@/pages/ReviewPhase";
import DeployPhase from "@/pages/DeployPhase";
import SkillLibrary from "@/pages/SkillLibrary";
import TokenControls from "@/pages/TokenControls";
import Login from "@/pages/Login";
import { verifyToken, logout as apiLogout } from "@/lib/api";

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
          <Route path="/code-review" element={<CodeReview />} />
          <Route path="/build" element={<BuildPhase />} />
          <Route path="/review" element={<ReviewPhase />} />
          <Route path="/deploy" element={<DeployPhase />} />
          <Route path="/skills" element={<SkillLibrary />} />
          <Route path="/token-controls" element={<TokenControls />} />
          <Route path="/stages/:stage" element={<StagePage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
