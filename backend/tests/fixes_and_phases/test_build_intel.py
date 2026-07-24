"""Unit tests for Phase 1 Build Intelligence — semantic chunking, embedding, retrieval, indexing."""

import json
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from app.services.build_intel.chunker import chunk_file
from app.services.build_intel.retriever import _cosine_similarity, search
from app.models import CodeEmbedding, Repo


class TestChunker:
    """Boundary-aware chunking against real Python/unknown-language content."""

    def test_splits_python_at_function_boundaries(self):
        code = (
            "import os\n\n"
            "def foo():\n    return 1\n\n"
            "def bar():\n    return 2\n"
        )
        chunks = chunk_file(code, "python")
        names = [c["symbol_name"] for c in chunks if c["symbol_name"]]
        assert "foo" in names
        assert "bar" in names

    def test_preamble_before_first_function_is_kept(self):
        code = "import os\nimport sys\n\ndef foo():\n    return 1\n"
        chunks = chunk_file(code, "python")
        # The import lines shouldn't be silently dropped
        assert any("import os" in c["content"] for c in chunks)

    def test_unknown_language_falls_back_to_fixed_size(self):
        code = "\n".join(f"line {i}" for i in range(200))
        chunks = chunk_file(code, "cobol")  # not in PATTERNS
        assert len(chunks) > 1
        assert all(c["symbol_name"] is None for c in chunks)

    def test_empty_content_returns_no_chunks(self):
        assert chunk_file("", "python") == []
        assert chunk_file("   \n  \n", "python") == []

    def test_oversized_function_gets_sub_split(self):
        body = "\n".join(f"    x{i} = {i}" for i in range(300))
        code = f"def huge():\n{body}\n"
        chunks = chunk_file(code, "python")
        assert len(chunks) > 1

    def test_line_numbers_are_sequential_and_valid(self):
        code = "def a():\n    pass\n\ndef b():\n    pass\n"
        chunks = chunk_file(code, "python")
        for c in chunks:
            assert c["line_start"] >= 1
            assert c["line_end"] >= c["line_start"]


class TestCosineSimilarity:
    def test_identical_vectors_score_near_one(self):
        v = [1.0, 2.0, 3.0]
        assert _cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors_score_zero(self):
        assert _cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_opposite_vectors_score_negative_one(self):
        assert _cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)

    def test_mismatched_lengths_return_zero_not_error(self):
        assert _cosine_similarity([1.0, 2.0], [1.0, 2.0, 3.0]) == 0.0

    def test_zero_vector_returns_zero_not_divide_error(self):
        assert _cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0

    def test_empty_vectors_return_zero(self):
        assert _cosine_similarity([], []) == 0.0


class TestSearch:
    """search() against a mocked DB + mocked embed_query — no real OpenAI calls."""

    @pytest.fixture
    def db_mock(self):
        return Mock(spec=Session)

    def test_returns_empty_when_no_index_exists(self, db_mock, monkeypatch):
        db_mock.query().filter().all.return_value = []
        results = search(db_mock, repo_id=1, query="anything")
        assert results == []

    def test_returns_top_k_sorted_by_similarity(self, db_mock, monkeypatch):
        from app.services.build_intel import retriever

        monkeypatch.setattr(retriever, "embed_query", lambda q, user_id=None: [1.0, 0.0])

        row_low = Mock(spec=CodeEmbedding, file_path="a.py", content="a", line_start=1, line_end=2,
                        symbol_name=None, embedding=json.dumps([0.0, 1.0]))  # orthogonal -> 0 similarity
        row_high = Mock(spec=CodeEmbedding, file_path="b.py", content="b", line_start=1, line_end=2,
                         symbol_name="foo", embedding=json.dumps([1.0, 0.0]))  # identical -> 1.0 similarity

        db_mock.query().filter().all.return_value = [row_low, row_high]

        results = search(db_mock, repo_id=1, query="find foo", top_k=2)
        assert results[0]["file_path"] == "b.py"
        assert results[0]["similarity"] == pytest.approx(1.0)
        assert results[1]["file_path"] == "a.py"

    def test_malformed_embedding_row_is_skipped_not_fatal(self, db_mock, monkeypatch):
        from app.services.build_intel import retriever

        monkeypatch.setattr(retriever, "embed_query", lambda q, user_id=None: [1.0, 0.0])
        bad_row = Mock(spec=CodeEmbedding, file_path="broken.py", content="x", line_start=1,
                        line_end=1, symbol_name=None, embedding="not json")
        db_mock.query().filter().all.return_value = [bad_row]

        results = search(db_mock, repo_id=1, query="q")
        assert results == []  # skipped, no crash


class TestIndexerValidation:
    """index_repo_semantic's guard clauses — same shape as auto_indexer.index_repo."""

    @pytest.fixture
    def db_mock(self):
        return Mock(spec=Session)

    def test_missing_repo_returns_error(self, db_mock):
        from app.services.build_intel.indexer import index_repo_semantic

        db_mock.query().filter().first.return_value = None
        result = index_repo_semantic(db_mock, repo_id=999)
        assert "error" in result

    def test_uncloned_repo_returns_error(self, db_mock):
        from app.services.build_intel.indexer import index_repo_semantic

        repo = Mock(spec=Repo, clone_status="not_cloned", local_path=None)
        db_mock.query().filter().first.return_value = repo
        result = index_repo_semantic(db_mock, repo_id=1)
        assert "error" in result

    def test_missing_clone_directory_returns_error(self, db_mock, tmp_path, monkeypatch):
        from app.services.build_intel.indexer import index_repo_semantic

        repo = Mock(spec=Repo, clone_status="cloned", local_path=str(tmp_path / "does_not_exist"))
        db_mock.query().filter().first.return_value = repo
        result = index_repo_semantic(db_mock, repo_id=1)
        assert "error" in result


class TestIndexerEndToEnd:
    """Real file walking + chunking against a tmp_path fake repo, mocked embeddings only."""

    def test_indexes_a_small_python_repo(self, tmp_path, monkeypatch):
        from app.services.build_intel import indexer as indexer_mod

        (tmp_path / "app.py").write_text("def hello():\n    return 'hi'\n", encoding="utf-8")
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "skip_me.py").write_text("def skipped(): pass\n", encoding="utf-8")

        repo = Mock(spec=Repo, id=1, clone_status="cloned", local_path=str(tmp_path))
        db = Mock(spec=Session)
        db.query().filter().first.return_value = repo

        captured_adds = []
        db.add.side_effect = lambda obj: captured_adds.append(obj)

        monkeypatch.setattr(
            indexer_mod, "embed_texts",
            lambda texts, user_id=None: [[0.1, 0.2] for _ in texts],
        )

        result = indexer_mod.index_repo_semantic(db, repo_id=1)

        assert result["status"] == "indexed"
        assert result["files_scanned"] == 1  # node_modules is skipped
        assert result["chunks_added"] >= 1
        assert len(captured_adds) == result["chunks_added"]
        assert all(json.loads(obj.embedding) == [0.1, 0.2] for obj in captured_adds)

    def test_reindex_deletes_previous_chunks_first(self, tmp_path, monkeypatch):
        from app.services.build_intel import indexer as indexer_mod

        (tmp_path / "app.py").write_text("def hello():\n    return 1\n", encoding="utf-8")
        repo = Mock(spec=Repo, id=1, clone_status="cloned", local_path=str(tmp_path))
        db = Mock(spec=Session)
        db.query().filter().first.return_value = repo

        delete_called = []
        db.query().filter().delete = lambda: delete_called.append(True)

        monkeypatch.setattr(indexer_mod, "embed_texts", lambda texts, user_id=None: [[0.1] for _ in texts])

        indexer_mod.index_repo_semantic(db, repo_id=1)
        assert delete_called


class TestBuildPhaseUsesRetrieval:
    """The actual Build generation path prefers semantic retrieval over the
    static snapshot once an index exists, and falls back cleanly when it doesn't."""

    def test_generate_core_uses_semantic_hits_when_available(self, monkeypatch):
        from app.services.phases import build_phase_svc

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setattr(
            "app.services.build_intel.retriever.search",
            lambda db, repo_id, query, top_k=6, user_id=None: [
                {"file_path": "auth.py", "content": "def login(): ...", "line_start": 1, "line_end": 1, "symbol_name": "login", "similarity": 0.9}
            ],
        )

        captured_prompts = {}

        class FakeCompleted(dict):
            pass

        def fake_complete_with_continuations(client, messages, **kwargs):
            captured_prompts["messages"] = messages
            return {"content": "FILE_PATH: x.py\nLANGUAGE: python\nEXPLANATION: ok\n```python\npass\n```",
                    "tokens_used": 10, "prompt_tokens": 8, "completion_tokens": 2,
                    "finish_reason": "stop", "structure_ok": True}

        monkeypatch.setattr(
            "app.services.quality.truncation.complete_with_continuations",
            fake_complete_with_continuations,
        )
        monkeypatch.setattr("app.token_tracker.log_tokens", lambda **kw: None)

        # Minimal stand-in matching the attributes _generate_core actually reads
        class Req:
            plan_step = "add login endpoint"
            project_context = None
            tech_stack = ""
            repo_id = 1
            file_path = "auth.py"
            write_to_repo = False

        # No local clone for this repo_id — Phase 2's diff lookup should no-op cleanly
        db = Mock(spec=Session)
        db.query().filter().first.return_value = None
        result = build_phase_svc._generate_core(Req(), db=db, workspace="", user_id=42)

        assert result["offline"] is False
        user_msg = captured_prompts["messages"][1]["content"]
        assert "auth.py" in user_msg
        assert "def login()" in user_msg

    def test_generate_core_falls_back_when_no_index(self, monkeypatch):
        from app.services.phases import build_phase_svc

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setattr(
            "app.services.build_intel.retriever.search",
            lambda db, repo_id, query, top_k=6, user_id=None: [],  # no index yet
        )
        monkeypatch.setattr(
            "app.routers.llm._build_repo_context",
            lambda db, repo_id, max_chars=4000: "STATIC SNAPSHOT CONTEXT",
        )

        captured_prompts = {}

        def fake_complete_with_continuations(client, messages, **kwargs):
            captured_prompts["messages"] = messages
            return {"content": "FILE_PATH: x.py\nLANGUAGE: python\nEXPLANATION: ok\n```python\npass\n```",
                    "tokens_used": 5, "prompt_tokens": 4, "completion_tokens": 1,
                    "finish_reason": "stop", "structure_ok": True}

        monkeypatch.setattr(
            "app.services.quality.truncation.complete_with_continuations",
            fake_complete_with_continuations,
        )
        monkeypatch.setattr("app.token_tracker.log_tokens", lambda **kw: None)

        class Req:
            plan_step = "add login endpoint"
            project_context = None
            tech_stack = ""
            repo_id = 1
            file_path = "auth.py"
            write_to_repo = False

        db = Mock(spec=Session)
        db.query().filter().first.return_value = None
        build_phase_svc._generate_core(Req(), db=db, workspace="", user_id=None)
        assert "STATIC SNAPSHOT CONTEXT" in captured_prompts["messages"][1]["content"]
