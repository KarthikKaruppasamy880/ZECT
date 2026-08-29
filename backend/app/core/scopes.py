"""Data classification / sharing scopes — backend-enforced isolation."""

from __future__ import annotations

USER_PRIVATE = "USER_PRIVATE"
TEAM_SHARED = "TEAM_SHARED"
PROJECT_SHARED = "PROJECT_SHARED"
ORG_SHARED = "ORG_SHARED"
SYSTEM = "SYSTEM"

SCOPES = (USER_PRIVATE, TEAM_SHARED, PROJECT_SHARED, ORG_SHARED, SYSTEM)

# Personal surfaces must default to USER_PRIVATE
PERSONAL_DEFAULT_SCOPE = USER_PRIVATE

# Repo intelligence (Lattice/Blueprint/Knowledge bound to repo+commit) may be
# PROJECT_SHARED for authorized project members — never per-user duplicates.
REPO_INTELLIGENCE_SCOPE = PROJECT_SHARED
