"""Explorer tree must surface saved PLAN.md files under .zect/plans/.

_build_tree() (backend/app/domains/repository/file_explorer.py) excluded any
entry whose name started with "." -- which silently swallowed the entire
`.zect` directory. Since PLAN.md files are saved to
`<workspace>/.zect/plans/<slug>.plan.md` (plan_store.py), a saved plan could
never appear in the Explorer tree, refresh or not, even though it was still
reachable via the separate "open in Monaco" button. `.git` and other
conventionally-hidden directories must remain excluded.
"""
from __future__ import annotations


def _find(nodes, name):
    for node in nodes:
        if node["name"] == name:
            return node
    return None


def test_tree_shows_zect_plan_but_hides_git_and_node_modules(tmp_path, authed_client):
    ws = tmp_path / "repo"
    plans_dir = ws / ".zect" / "plans"
    plans_dir.mkdir(parents=True)
    (plans_dir / "my-feature.plan.md").write_text("# plan", encoding="utf-8")
    (ws / ".git").mkdir()
    (ws / ".git" / "HEAD").write_text("ref: refs/heads/develop", encoding="utf-8")
    (ws / "node_modules").mkdir()
    (ws / "node_modules" / "pkg.js").write_text("", encoding="utf-8")
    (ws / "README.md").write_text("hi", encoding="utf-8")

    resp = authed_client.get("/api/files/tree", params={"path": str(ws), "depth": 5})
    assert resp.status_code == 200
    tree = resp.json()

    assert _find(tree, ".git") is None
    assert _find(tree, "node_modules") is None
    assert _find(tree, "README.md") is not None

    zect_node = _find(tree, ".zect")
    assert zect_node is not None
    plans_node = _find(zect_node["children"], "plans")
    assert plans_node is not None
    plan_file = _find(plans_node["children"], "my-feature.plan.md")
    assert plan_file is not None
    assert plan_file["is_dir"] is False
