import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const fetchMock = vi.fn();

vi.mock("@/contexts/ActiveProjectContext", () => ({
  useActiveProject: () => ({
    activeProjectId: 7,
    activeRepoId: 199,
    activeProjectKey: "zinnia-zaf-devin",
    activeLocalPath: "C:\\repos\\zaf",
    activeRepo: { owner: "zinnia", repo_name: "ZAF-devin", repo_id: 199 },
  }),
}));

vi.mock("@/lib/api", () => ({
  authHeaders: () => ({}),
  getApiBase: () => "http://localhost:8020",
  indexClonedRepo: vi.fn(),
  latticeIngest: vi.fn(),
}));

import ProjectIntelligencePage from "./ProjectIntelligence";

describe("ProjectIntelligencePage", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({
        lattice: {
          state: "READY",
          status: "READY",
          repository_id: 199,
          project_key: "zinnia-zaf-devin",
          action_label: "Lattice READY",
          hits: [{ id: "n1", text: "HealthEndpoint", summary: "graph node" }],
        },
        knowledge: [],
        memory: [],
      }),
    });
    vi.stubGlobal("fetch", fetchMock);
  });

  it("loads intelligence for the header project and repository", async () => {
    render(
      <MemoryRouter>
        <ProjectIntelligencePage />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });
    const url = String(fetchMock.mock.calls[0][0]);
    expect(url).toContain("project_id=7");
    expect(url).toContain("project_key=zinnia-zaf-devin");
    expect(url).toContain("repository_id=199");
    expect(screen.getByTestId("pi-bound-repo")).toHaveTextContent("Lattice READY");
    expect(screen.getByTestId("pi-lattice-hits")).toHaveTextContent("HealthEndpoint");
    expect(screen.queryByTestId("pi-reindex-hint")).toBeNull();
  });
});
