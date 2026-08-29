"""Evidence-based performance/reliability thresholds.

Declared BEFORE interpreting load/soak results. Do not raise these after a
failing run just to obtain PASS. Values are SLOs for the synthetic fixtures in
``tests/test_performance_reliability_production.py`` on local desktop_sqlite.
"""

from __future__ import annotations

# Lattice product cap remains 2000 files (indexer.py). CI fixture stays below that.
LATTICE_INGEST_FILES = 120
LATTICE_INGEST_MAX_MS = 25_000

WORKSPACE_ROOTS = 3
WORKSPACE_SEARCH_MAX_MS = 8_000

CONCURRENT_WORKITEMS = 3
CONCURRENT_MISSIONS = 2
CODING_ISOLATE_MAX_MS = 20_000

# Restricted Present fail-closed must not call an external engine.
PRESENT_RESTRICTED_FAIL_MAX_MS = 3_000
PRESENT_FAST_PLAN_MAX_MS = 8_000

SOAK_ITERATIONS = 8
SOAK_LATTICE_FILES = 16
SOAK_MAX_RSS_GROWTH_BYTES = 96 * 1024 * 1024
SOAK_MAX_DB_CHECKEDOUT = 8
SOAK_MAX_HANDLE_GROWTH = 200
SOAK_MAX_TEMP_GROWTH_BYTES = 32 * 1024 * 1024

CANCEL_INDEX_MAX_MS = 8_000
CANCEL_PRESENT_MAX_MS = 3_000
CANCEL_MISSION_MAX_MS = 5_000

ISOLATION_LEAKS_ALLOWED = 0

# Declared before interpreting overlapping-thread / Companion soak / native Quality
# results on canonical develop a73fd02 (PR #164 merged). Do not raise after a fail.
COMPANION_CONCURRENT_SESSIONS = 3
COMPANION_CONCURRENT_MAX_MS = 45_000
OVERLAPPING_THREADS = 2
OVERLAPPING_ISOLATE_MAX_MS = 30_000
TERMINAL_CONCURRENT = 2
TERMINAL_SOAK_MAX_MS = 25_000
PRESENT_NATIVE_QUALITY_SLIDES = 5
PRESENT_NATIVE_QUALITY_MAX_MS = 45_000
PRESENT_NATIVE_QUALITY_LOAD = 3
CONCURRENT_LOAD_SOAK_MAX_MS = 60_000
