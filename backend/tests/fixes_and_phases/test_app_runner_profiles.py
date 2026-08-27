"""App Runner run-profile persistence + broader manifest discovery + real
affected-service restart (V2 closure §14).

Previously discover_runtime_recipes() only understood npm/Python manifests,
never persisted a confirmed choice (recomputed from scratch on every call),
and "restart" always meant stop-everything-in-the-workspace-then-respawn --
there was no way to restart just the one service that was actually affected
by an edit without disturbing a sibling process in the same workspace."""

from __future__ import annotations

from pathlib import Path

from app.services.workspace.runtime_discovery import (
    discover_runtime_recipes,
    load_confirmed_profile,
    save_confirmed_profile,
)


class TestBroaderManifestDiscovery:
    def test_docker_compose_yields_a_full_recipe(self, tmp_path):
        (tmp_path / "docker-compose.yml").write_text("services:\n  web:\n    build: .\n", encoding="utf-8")
        out = discover_runtime_recipes(str(tmp_path))
        assert any(r["id"] == "docker-compose-up" and r["command"] == "docker compose up" for r in out["recipes"])

    def test_maven_pom_yields_backend_and_test_recipes(self, tmp_path):
        (tmp_path / "pom.xml").write_text("<project></project>", encoding="utf-8")
        out = discover_runtime_recipes(str(tmp_path))
        ids = {r["id"] for r in out["recipes"]}
        assert "maven-run" in ids
        assert "maven-test" in ids

    def test_gradle_build_file_yields_gradlew_recipes(self, tmp_path):
        (tmp_path / "build.gradle").write_text("plugins { }\n", encoding="utf-8")
        out = discover_runtime_recipes(str(tmp_path))
        ids = {r["id"] for r in out["recipes"]}
        assert "gradle-run" in ids
        assert "gradle-test" in ids
        run = next(r for r in out["recipes"] if r["id"] == "gradle-run")
        assert run["command"] == "./gradlew bootRun"

    def test_makefile_offers_only_known_run_shaped_targets(self, tmp_path):
        (tmp_path / "Makefile").write_text(
            "run:\n\techo run\n\nclean:\n\trm -rf build\n\ndeploy:\n\techo deploy\n", encoding="utf-8"
        )
        out = discover_runtime_recipes(str(tmp_path))
        ids = {r["id"] for r in out["recipes"]}
        assert "make-run" in ids
        # "clean" and "deploy" are not run-shaped targets ZECT should offer to start.
        assert "make-clean" not in ids
        assert "make-deploy" not in ids


class TestConfirmedProfilePersistence:
    def test_save_and_load_round_trips(self, tmp_path):
        recipe = {"id": "py-backend", "kind": "backend", "command": "uvicorn app.main:app"}
        result = save_confirmed_profile(str(tmp_path), recipe)
        assert result["ok"] is True
        assert Path(result["path"]).is_file()

        loaded = load_confirmed_profile(str(tmp_path))
        assert loaded is not None
        assert loaded["recipe_id"] == "py-backend"
        assert loaded["recipe"]["command"] == "uvicorn app.main:app"

    def test_load_returns_none_when_never_confirmed(self, tmp_path):
        assert load_confirmed_profile(str(tmp_path)) is None

    def test_discover_prefers_the_confirmed_profile_as_default_id(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
        first = discover_runtime_recipes(str(tmp_path))
        assert first["default_id"] == "py-backend"  # the only "full"-less backend/tests pair -> first found

        # Confirm the tests recipe explicitly, even though it wouldn't be the
        # natural default -- the next discovery call must honor that choice.
        py_tests = next(r for r in first["recipes"] if r["id"] == "py-tests")
        save_confirmed_profile(str(tmp_path), py_tests)

        second = discover_runtime_recipes(str(tmp_path))
        assert second["default_id"] == "py-tests"
        assert second["confirmed_profile"]["recipe_id"] == "py-tests"
