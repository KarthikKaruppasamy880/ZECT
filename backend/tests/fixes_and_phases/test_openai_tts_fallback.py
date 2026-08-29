from app.adapters.llm.openai_tts import openai_tts_available


def test_openai_tts_available_false_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert openai_tts_available() is False


def test_openai_tts_available_true_with_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert openai_tts_available() is True
