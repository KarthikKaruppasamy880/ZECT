"""Zinnia Dream Engine — automated pattern extraction, candidate staging, decay."""

import math
from datetime import datetime, timezone, timedelta
from typing import Optional
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    EpisodicMemory, Lesson, WorkingMemory, DreamCycleRun,
)

router = APIRouter(prefix="/api/dream", tags=["dream-engine"])

CLUSTER_SIMILARITY = 0.3
PROMOTION_THRESHOLD = 3  # min occurrences to promote
DECAY_MAX_AGE_DAYS = 30
WORKSPACE_INACTIVE_DAYS = 2


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class DreamCycleRequest(BaseModel):
    project_id: int
    max_age_days: int = 14
    cluster_threshold: float = CLUSTER_SIMILARITY
    min_occurrences: int = PROMOTION_THRESHOLD


class ManualDecay(BaseModel):
    project_id: int
    max_age_days: int = DECAY_MAX_AGE_DAYS


# ---------------------------------------------------------------------------
# Dream Cycle — the core learning loop
# ---------------------------------------------------------------------------

@router.post("/run")
def run_dream_cycle(data: DreamCycleRequest, db: Session = Depends(get_db)):
    """Execute a dream cycle: cluster episodes → stage candidates → prefilter → decay."""
    run = DreamCycleRun(project_id=data.project_id, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        # Stage 1: Load recent episodic entries
        cutoff = datetime.now(timezone.utc) - timedelta(days=data.max_age_days)
        episodes = db.query(EpisodicMemory).filter(
            EpisodicMemory.project_id == data.project_id,
            EpisodicMemory.is_decayed == False,
            EpisodicMemory.created_at >= cutoff,
        ).order_by(EpisodicMemory.created_at.desc()).all()

        run.episodes_processed = len(episodes)

        # Stage 2: Cluster by lexical similarity
        clusters = _cluster_episodes(episodes, data.cluster_threshold)
        run.clusters_found = len(clusters)

        # Stage 3: Extract patterns from clusters (>= min_occurrences)
        candidates_staged = 0
        for cluster in clusters:
            if len(cluster) < data.min_occurrences:
                continue
            # Extract common pattern
            pattern = _extract_pattern(cluster)
            if not pattern:
                continue
            # Check if already staged
            existing = db.query(Lesson).filter(
                Lesson.project_id == data.project_id,
                Lesson.claim == pattern["claim"],
                Lesson.status.in_(["staged", "accepted", "provisional"]),
            ).first()
            if existing:
                existing.evidence_count = max(existing.evidence_count, len(cluster))
                existing.cluster_size = len(cluster)
                continue

            # Stage new candidate
            lesson = Lesson(
                project_id=data.project_id,
                claim=pattern["claim"],
                conditions=pattern.get("conditions", []),
                status="staged",
                confidence=pattern.get("confidence", 0.5),
                evidence_count=len(cluster),
                cluster_size=len(cluster),
                canonical_salience=pattern.get("salience", 0.5),
            )
            db.add(lesson)
            candidates_staged += 1

        run.candidates_staged = candidates_staged

        # Stage 4: Heuristic prefilter — remove obvious junk
        prefiltered = _prefilter_candidates(db, data.project_id)
        run.candidates_prefiltered = prefiltered

        # Stage 5: Decay old episodes
        decay_cutoff = datetime.now(timezone.utc) - timedelta(days=DECAY_MAX_AGE_DAYS)
        old_episodes = db.query(EpisodicMemory).filter(
            EpisodicMemory.project_id == data.project_id,
            EpisodicMemory.is_decayed == False,
            EpisodicMemory.created_at < decay_cutoff,
        ).all()
        for ep in old_episodes:
            ep.is_decayed = True
        run.episodes_decayed = len(old_episodes)

        # Stage 6: Archive stale working memory
        ws_cutoff = datetime.now(timezone.utc) - timedelta(days=WORKSPACE_INACTIVE_DAYS)
        stale_workspaces = db.query(WorkingMemory).filter(
            WorkingMemory.project_id == data.project_id,
            WorkingMemory.status == "active",
            WorkingMemory.updated_at < ws_cutoff,
        ).all()
        for ws in stale_workspaces:
            ws.status = "archived"
            ws.archived_at = datetime.now(timezone.utc)
        run.workspaces_archived = len(stale_workspaces)

        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)

        return _serialize_run(run)

    except Exception as exc:
        run.status = "failed"
        run.error_message = str(exc)
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(500, f"Dream cycle failed: {exc}")


@router.get("/runs/{project_id}")
def list_dream_runs(project_id: int, limit: int = 10, db: Session = Depends(get_db)):
    runs = db.query(DreamCycleRun).filter(
        DreamCycleRun.project_id == project_id,
    ).order_by(DreamCycleRun.started_at.desc()).limit(limit).all()
    return [_serialize_run(r) for r in runs]


@router.get("/runs/detail/{run_id}")
def get_dream_run(run_id: int, db: Session = Depends(get_db)):
    run = db.query(DreamCycleRun).filter(DreamCycleRun.id == run_id).first()
    if not run:
        raise HTTPException(404, "Dream cycle run not found")
    return _serialize_run(run)


@router.post("/decay")
def manual_decay(data: ManualDecay, db: Session = Depends(get_db)):
    """Manually trigger decay of old episodes."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=data.max_age_days)
    old_episodes = db.query(EpisodicMemory).filter(
        EpisodicMemory.project_id == data.project_id,
        EpisodicMemory.is_decayed == False,
        EpisodicMemory.created_at < cutoff,
    ).all()
    for ep in old_episodes:
        ep.is_decayed = True
    db.commit()
    return {"decayed": len(old_episodes)}


# ---------------------------------------------------------------------------
# Clustering & Pattern Extraction
# ---------------------------------------------------------------------------

def _cluster_episodes(episodes: list, threshold: float) -> list:
    """Cluster episodes by lexical similarity."""
    if not episodes:
        return []

    clusters = []
    used = set()

    for i, ep in enumerate(episodes):
        if i in used:
            continue
        cluster = [ep]
        used.add(i)
        words_i = set(f"{ep.action} {ep.outcome}".lower().split())

        for j in range(i + 1, len(episodes)):
            if j in used:
                continue
            words_j = set(f"{episodes[j].action} {episodes[j].outcome}".lower().split())
            if not words_i or not words_j:
                continue
            overlap = len(words_i & words_j) / max(len(words_i | words_j), 1)
            if overlap >= threshold:
                cluster.append(episodes[j])
                used.add(j)

        clusters.append(cluster)

    return clusters


def _extract_pattern(cluster: list) -> dict:
    """Extract a common pattern from a cluster of episodes."""
    if not cluster:
        return {}

    # Find most common action
    actions = defaultdict(int)
    for ep in cluster:
        actions[ep.action] += 1
    most_common_action = max(actions, key=actions.get)

    # Build claim from common elements
    outcomes = [ep.outcome for ep in cluster if ep.outcome]
    successes = [ep for ep in cluster if ep.success]
    failures = [ep for ep in cluster if not ep.success]

    if len(failures) > len(successes):
        claim = f"When performing '{most_common_action}', failures are common — consider alternative approaches"
    else:
        claim = f"Pattern: '{most_common_action}' succeeds reliably with {len(successes)}/{len(cluster)} success rate"

    # Conditions from reflections
    conditions = []
    reflections = [ep.reflection for ep in cluster if ep.reflection]
    if reflections:
        conditions.append(f"Observed in {len(cluster)} episodes")

    # Average salience
    avg_salience = sum(ep.salience for ep in cluster) / len(cluster)
    avg_confidence = sum(ep.confidence for ep in cluster) / len(cluster)

    return {
        "claim": claim,
        "conditions": conditions,
        "salience": round(avg_salience, 2),
        "confidence": round(avg_confidence, 2),
    }


def _prefilter_candidates(db: Session, project_id: int) -> int:
    """Remove obvious junk candidates — too short, exact duplicates."""
    candidates = db.query(Lesson).filter(
        Lesson.project_id == project_id,
        Lesson.status == "staged",
    ).all()

    rejected = 0
    seen_claims = set()
    for c in candidates:
        # Too-short claims
        if len(c.claim) < 10:
            c.status = "rejected"
            c.rejection_reason = "Auto-rejected: claim too short"
            c.rejection_count = (c.rejection_count or 0) + 1
            rejected += 1
            continue
        # Exact duplicate
        if c.claim in seen_claims:
            c.status = "rejected"
            c.rejection_reason = "Auto-rejected: exact duplicate"
            c.rejection_count = (c.rejection_count or 0) + 1
            rejected += 1
            continue
        seen_claims.add(c.claim)

    db.commit()
    return rejected


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

def _serialize_run(r: DreamCycleRun) -> dict:
    return {
        "id": r.id, "project_id": r.project_id, "status": r.status,
        "episodes_processed": r.episodes_processed,
        "clusters_found": r.clusters_found,
        "candidates_staged": r.candidates_staged,
        "candidates_prefiltered": r.candidates_prefiltered,
        "episodes_decayed": r.episodes_decayed,
        "workspaces_archived": r.workspaces_archived,
        "error_message": r.error_message,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
    }
