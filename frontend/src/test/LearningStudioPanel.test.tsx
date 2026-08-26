import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import LearningStudioPanel from "@/components/LearningStudioPanel";

vi.mock("@/hooks/useWorkspaceRepoContext", () => ({
  useWorkspaceRepoContext: () => ({ projectKey: "demo-project" }),
}));

vi.mock("@/lib/api", () => ({
  authHeaders: () => ({}),
}));

function mockFetchOnce(body: unknown, ok = true) {
  return vi.fn().mockResolvedValueOnce({
    ok,
    json: async () => body,
  });
}

describe("LearningStudioPanel", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("shows a re-index prompt instead of any content when the index is not READY", async () => {
    global.fetch = mockFetchOnce({ status: { state: "NOT_INDEXED" }, topics: [] });
    render(<LearningStudioPanel />);

    await waitFor(() => {
      expect(screen.getByTestId("learning-studio-not-ready")).toBeInTheDocument();
    });
    expect(screen.getByTestId("learning-studio-not-ready").textContent).toContain("NOT_INDEXED");
    expect(screen.queryByTestId("learning-studio-catalog")).not.toBeInTheDocument();
  });

  it("renders grounded catalog topics with citations when READY", async () => {
    global.fetch = mockFetchOnce({
      status: { state: "READY" },
      topics: [
        {
          topic_id: "knowledge:1",
          title: "Deploy runbook",
          kind: "knowledge",
          source_refs: [{ type: "knowledge", id: "1", title: "Deploy runbook" }],
        },
      ],
    });
    render(<LearningStudioPanel />);

    await waitFor(() => {
      expect(screen.getByTestId("learning-studio-catalog")).toBeInTheDocument();
    });
    expect(screen.getByTestId("learning-studio-topic-knowledge:1").textContent).toContain("Deploy runbook");
  });
});
