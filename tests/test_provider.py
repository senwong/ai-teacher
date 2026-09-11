import os

from app.llm import provider


def test_deepseek_provider_defaults(monkeypatch):
    for key in (
        "AI_PROVIDER", "AI_API_KEY", "AI_BASE_URL", "AI_MODEL", "AI_VISION_MODEL",
        "DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL", "DEEPSEEK_VISION_MODEL",
        "OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL", "OPENAI_VISION_MODEL",
    ):
        monkeypatch.delenv(key, raising=False)

    monkeypatch.setenv("AI_PROVIDER", "deepseek")
    monkeypatch.setenv("AI_API_KEY", "test-key")

    assert provider.provider_name() == "deepseek"
    assert provider.api_key() == "test-key"
    assert provider.base_url() == "https://api.deepseek.com"
    assert provider.text_model() == "deepseek-v4-flash"
    assert provider.vision_model() == "deepseek-v4-flash-vision-exp"
    assert provider.enabled() is True


def test_generic_ai_vars_override_provider_specific_vars(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "deepseek")
    monkeypatch.setenv("AI_API_KEY", "generic-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")
    monkeypatch.setenv("AI_BASE_URL", "https://example.test/v1/")
    monkeypatch.setenv("AI_MODEL", "text-model")
    monkeypatch.setenv("AI_VISION_MODEL", "vision-model")

    assert provider.api_key() == "generic-key"
    assert provider.base_url() == "https://example.test/v1"
    assert provider.text_model() == "text-model"
    assert provider.vision_model() == "vision-model"


def test_legacy_openai_environment_is_still_supported(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.delenv("AI_BASE_URL", raising=False)
    monkeypatch.delenv("AI_MODEL", raising=False)
    monkeypatch.delenv("AI_VISION_MODEL", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "legacy-key")
    monkeypatch.setenv("OPENAI_MODEL", "legacy-text")
    monkeypatch.setenv("OPENAI_VISION_MODEL", "legacy-vision")

    assert provider.provider_name() == "openai"
    assert provider.api_key() == "legacy-key"
    assert provider.text_model() == "legacy-text"
    assert provider.vision_model() == "legacy-vision"
