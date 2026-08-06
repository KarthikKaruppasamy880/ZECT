"""Labs productivity spine — knowledge context + playbook variable substitution."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.domains.personal_agent.playbook_executor import substitute_variables
from app.domains.repository.knowledge_base import retrieve_knowledge_for_context
from app.infrastructure.database import Base
from app.models import KnowledgeEntry


def test_substitute_variables():
    assert substitute_variables("Hello {{name}}", {"name": "ZECT"}) == "Hello ZECT"
    assert substitute_variables("{{ a }}-{{b}}", {"a": "1", "b": "2"}) == "1-2"
    assert substitute_variables("keep {{missing}}", {}) == "keep {{missing}}"


def test_retrieve_knowledge_for_context():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    e = KnowledgeEntry(
        title="API style",
        content="Prefer FastAPI routers under domains/",
        category="coding",
        tags=["api"],
        is_active=True,
    )
    db.add(e)
    db.commit()

    block, meta = retrieve_knowledge_for_context(db, query="FastAPI", max_tokens=200, limit=3)
    assert "Knowledge Base" in block
    assert "API style" in block
    assert meta["entry_count"] >= 1
    assert meta["tokens_estimated"] >= 1
