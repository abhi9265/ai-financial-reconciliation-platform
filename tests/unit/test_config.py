from reconciliation_platform.config import Settings


def test_settings_from_environment(monkeypatch):
    monkeypatch.setenv("RECONCILIATION_API_KEY", "secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
    monkeypatch.setenv("RECONCILIATION_DB", "tmp.db")
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setenv("AI_MODEL", "test-model")
    monkeypatch.setenv("AI_TIMEOUT_SECONDS", "5")
    monkeypatch.setenv("API_KEY_REQUIRED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret")

    settings = Settings.from_env()

    assert settings.api_key == "secret"
    assert settings.openai_api_key == "openai-secret"
    assert settings.database_url == "postgresql://localhost/test"
    assert settings.database_path == "tmp.db"
    assert settings.ai_provider == "openai"
    assert settings.ai_model == "test-model"
    assert settings.ai_timeout_seconds == 5
    assert settings.api_key_required is True
