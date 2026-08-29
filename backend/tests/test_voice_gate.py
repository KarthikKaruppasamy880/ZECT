from app.services.mentrix.voice_gate import passes_voice_gate, stage_voice_text


def test_voice_gate_rejects_short_fragments():
    assert stage_voice_text("it's") is None
    assert stage_voice_text("it has") is None
    assert stage_voice_text("as fast as") is None
    assert stage_voice_text("mentrix ready how can I help") is None


def test_voice_gate_accepts_real_questions():
    assert stage_voice_text("hi") == "hi"
    assert stage_voice_text("check my email inbox") == "check my email inbox"
    assert stage_voice_text("Hey Mentrix what's the weather in Austin") == "what's the weather in Austin"
    assert passes_voice_gate("open lattice docs graph")
