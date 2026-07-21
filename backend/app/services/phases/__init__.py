"""Callable phase wrappers for Mentrix ForgeLoop (no HTTP self-calls)."""

from app.services.phases.blueprint_phase import run_blueprint
from app.services.phases.llm_phase import run_ask, run_enhance_blueprint, run_plan
from app.services.phases.review_phase_svc import run_ultra_review

# build_phase_svc imported lazily via __getattr__ to keep light imports available


def __getattr__(name: str):
    if name in ("run_build_generate", "run_build_from_plan"):
        from app.services.phases.build_phase_svc import run_build_from_plan, run_build_generate

        return {"run_build_generate": run_build_generate, "run_build_from_plan": run_build_from_plan}[name]
    raise AttributeError(name)


__all__ = [
    "run_ask",
    "run_plan",
    "run_enhance_blueprint",
    "run_blueprint",
    "run_build_generate",
    "run_build_from_plan",
    "run_ultra_review",
]
