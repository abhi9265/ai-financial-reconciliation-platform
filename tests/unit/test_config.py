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


def test_queue_and_rate_limit_settings(monkeypatch):
    monkeypatch.setenv("JOB_QUEUE", "celery")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "10")
    settings = Settings.from_env()
    assert settings.job_queue == "celery"
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.rate_limit_per_minute == 10


def test_managed_database_configuration_builds_safe_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_HOST", "postgres.internal")
    monkeypatch.setenv("DATABASE_USER", "reconciliation")
    monkeypatch.setenv("DATABASE_PASSWORD", "secret password/with-specials")
    monkeypatch.setenv("DATABASE_NAME", "reconciliation")
    monkeypatch.setenv("DATABASE_PORT", "5432")

    settings = Settings.from_env()

    assert settings.database_url == (
        "postgresql://reconciliation:secret%20password%2Fwith-specials"
        "@postgres.internal:5432/reconciliation"
    )
