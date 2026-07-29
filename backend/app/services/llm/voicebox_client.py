"""Legacy alias — prefer app.services.llm.chatterbox_client.

Keeps older imports/tests working. Env VOICEBOX_* still honored as fallback
inside chatterbox_client.
"""

from __future__ import annotations

from app.services.llm.chatterbox_client import (  # noqa: F401
    CHATTERBOX_AUDIO_PATH_TEMPLATE as VOICEBOX_AUDIO_PATH_TEMPLATE,
    CHATTERBOX_BASE_URL as VOICEBOX_BASE_URL,
    chatterbox_available as voicebox_available,
    clone_voice,
    delete_voice,
    synthesize_speech,
)
