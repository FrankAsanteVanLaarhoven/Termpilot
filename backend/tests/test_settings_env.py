from __future__ import annotations

from app.settings import Settings, reset_settings_cache


def test_blank_vercel_env_uses_defaults(monkeypatch) -> None:
    monkeypatch.setenv("TERMPILOT_PORT", "")
    monkeypatch.setenv("GROK_MODE", "")
    monkeypatch.setenv("TERMPILOT_ENV", "production")
    monkeypatch.setenv("PLAN_HORIZON_DAYS", "")
    reset_settings_cache()
    settings = Settings()
    assert settings.env == "production"
    assert settings.port == 8000
    assert settings.grok_mode == "auto"
    assert settings.plan_horizon_days == 14
    reset_settings_cache()


def test_vercel_blank_env_is_production(monkeypatch) -> None:
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("TERMPILOT_ENV", "")
    reset_settings_cache()
    settings = Settings()
    assert settings.env == "production"
    assert settings.auth_from_email.startswith("TermPilot")
    assert "student@termpilot.org" in settings.auth_from_email
    reset_settings_cache()
