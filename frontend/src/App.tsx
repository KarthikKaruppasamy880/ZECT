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

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/projects/new" element={<CreateProject />} />
          <Route path="/projects/:id" element={<ProjectDetail />} />
          <Route path="/projects/:id/pr/:owner/:repo/:number" element={<PRViewer />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/orchestration" element={<Orchestration />} />
          <Route path="/docs" element={<Docs />} />
          <Route path="/stages/:stage" element={<StagePage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
