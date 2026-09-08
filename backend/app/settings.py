"""Runtime configuration. Secrets are read from the environment only."""

from __future__ import annotations

import os
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_ROOT = REPO_ROOT / "fixtures"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Literal["demo", "test", "production"] = Field(
        default_factory=lambda: (
            "production"
            if os.environ.get("VERCEL") and not (os.environ.get("TERMPILOT_ENV") or "").strip()
            else "demo"
        ),
        alias="TERMPILOT_ENV",
    )
    host: str = Field(default="127.0.0.1", alias="TERMPILOT_HOST")
    port: int = Field(default=8000, alias="TERMPILOT_PORT")
    frontend_origin: str = Field(default="http://127.0.0.1:3000", alias="TERMPILOT_FRONTEND_ORIGIN")
    cors_origins_extra: str = Field(default="", alias="TERMPILOT_CORS_ORIGINS")
    timezone: str = Field(default="Europe/London", alias="TERMPILOT_TIMEZONE")
    now_override: str | None = Field(default="2026-09-05T08:00:00+01:00", alias="TERMPILOT_NOW")
    demo_user_id: str = Field(default="FAVL", alias="TERMPILOT_DEMO_USER_ID")
    require_verification: bool = Field(default=False, alias="TERMPILOT_REQUIRE_VERIFICATION")
    access_code: str | None = Field(default=None, alias="TERMPILOT_ACCESS_CODE")
    university_domains_extra: str = Field(default="", alias="TERMPILOT_UNIVERSITY_DOMAINS")

    database_url: str = Field(default="sqlite+aiosqlite:///./termpilot.db", alias="DATABASE_URL")

    xai_api_key: str | None = Field(default=None, alias="XAI_API_KEY")
    xai_base_url: str = Field(default="https://api.x.ai/v1", alias="XAI_BASE_URL")
    xai_model: str = Field(default="grok-4.5", alias="XAI_MODEL")
    grok_mode: Literal["auto", "fake", "live"] = Field(default="auto", alias="GROK_MODE")
    openrouter_api_key: str | None = Field(default=None, alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL"
    )

    plan_horizon_days: int = Field(default=14, alias="PLAN_HORIZON_DAYS")
    max_study_block_minutes: int = Field(default=120, alias="MAX_STUDY_BLOCK_MINUTES")
    break_minutes: int = Field(default=15, alias="BREAK_MINUTES")
    safety_buffer_hours: int = Field(default=24, alias="SAFETY_BUFFER_HOURS")
    weekly_study_limit_hours: int = Field(default=20, alias="WEEKLY_STUDY_LIMIT_HOURS")

    raw_source_retention_hours: int = Field(default=72, alias="RAW_SOURCE_RETENTION_HOURS")
    approval_ttl_minutes: int = Field(default=30, alias="APPROVAL_TTL_MINUTES")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_json: bool = Field(default=True, alias="LOG_JSON")
    sentry_dsn: str | None = Field(default=None, alias="SENTRY_DSN")
    sentry_traces_sample_rate: float = Field(default=0.0, alias="SENTRY_TRACES_SAMPLE_RATE")

    simulate_lms_outage: bool = Field(default=False, alias="SIMULATE_LMS_OUTAGE")
    simulate_grok_timeout: bool = Field(default=False, alias="SIMULATE_GROK_TIMEOUT")
    simulate_calendar_write_failure: bool = Field(
        default=False, alias="SIMULATE_CALENDAR_WRITE_FAILURE"
    )
    simulate_offline: bool = Field(default=False, alias="SIMULATE_OFFLINE")

    fixtures_dir: Path | None = Field(default=None, alias="FIXTURES_ROOT")

    linkedin_client_id: str | None = Field(default=None, alias="LINKEDIN_CLIENT_ID")
    linkedin_client_secret: str | None = Field(default=None, alias="LINKEDIN_CLIENT_SECRET")
    orcid_client_id: str | None = Field(default=None, alias="ORCID_CLIENT_ID")
    orcid_client_secret: str | None = Field(default=None, alias="ORCID_CLIENT_SECRET")
    x_client_id: str | None = Field(default=None, alias="X_CLIENT_ID")
    x_client_secret: str | None = Field(default=None, alias="X_CLIENT_SECRET")
    notion_client_id: str | None = Field(default=None, alias="NOTION_CLIENT_ID")
    notion_client_secret: str | None = Field(default=None, alias="NOTION_CLIENT_SECRET")
    slack_client_id: str | None = Field(default=None, alias="SLACK_CLIENT_ID")
    slack_client_secret: str | None = Field(default=None, alias="SLACK_CLIENT_SECRET")
    google_client_id: str | None = Field(default=None, alias="GOOGLE_CLIENT_ID")
    google_client_secret: str | None = Field(default=None, alias="GOOGLE_CLIENT_SECRET")
    microsoft_client_id: str | None = Field(default=None, alias="MICROSOFT_CLIENT_ID")
    microsoft_client_secret: str | None = Field(default=None, alias="MICROSOFT_CLIENT_SECRET")
    canvas_client_id: str | None = Field(default=None, alias="CANVAS_CLIENT_ID")
    canvas_client_secret: str | None = Field(default=None, alias="CANVAS_CLIENT_SECRET")
    github_client_id: str | None = Field(default=None, alias="GITHUB_CLIENT_ID")
    github_client_secret: str | None = Field(default=None, alias="GITHUB_CLIENT_SECRET")
    jira_client_id: str | None = Field(default=None, alias="JIRA_CLIENT_ID")
    jira_client_secret: str | None = Field(default=None, alias="JIRA_CLIENT_SECRET")
    discord_client_id: str | None = Field(default=None, alias="DISCORD_CLIENT_ID")
    discord_client_secret: str | None = Field(default=None, alias="DISCORD_CLIENT_SECRET")
    resend_api_key: str | None = Field(default=None, alias="RESEND_API_KEY")
    smtp_url: str | None = Field(default=None, alias="SMTP_URL")
    auth_from_email: str = Field(
        default="TermPilot <student@termpilot.org>", alias="TERMPILOT_AUTH_FROM"
    )
    reply_to_email: str = Field(default="support@termpilot.org", alias="TERMPILOT_REPLY_TO")
    twilio_account_sid: str | None = Field(default=None, alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str | None = Field(default=None, alias="TWILIO_AUTH_TOKEN")
    twilio_from: str | None = Field(default=None, alias="TWILIO_FROM")
    session_days: int = Field(default=7, alias="TERMPILOT_SESSION_DAYS")

    @property
    def fixtures_root(self) -> Path:
        if self.fixtures_dir is not None:
            return Path(self.fixtures_dir)
        for candidate in (
            BACKEND_ROOT / "fixtures",
            REPO_ROOT / "fixtures",
            Path("/opt/termpilot/fixtures"),
            Path("/var/task/fixtures"),
            Path("/var/task/backend/fixtures"),
        ):
            if (candidate / "expected" / "reconciliation.json").exists():
                return candidate
        return FIXTURES_ROOT

    @model_validator(mode="before")
    @classmethod
    def drop_blank_env(cls, data: object) -> object:
        """Vercel often sets unused keys to ''. That must not fail int/literal fields."""
        if not isinstance(data, dict):
            cleaned: dict[str, object] = {}
        else:
            cleaned = {key: value for key, value in data.items() if value != ""}
        if os.environ.get("VERCEL") and not (os.environ.get("TERMPILOT_ENV") or "").strip():
            cleaned["env"] = "production"
        return cleaned

    @field_validator("env", mode="before")
    @classmethod
    def coerce_env(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        raw = value.strip().lower()
        if raw == "" and os.environ.get("VERCEL"):
            return "production"
        if raw in {"", "dev", "development", "demo"}:
            return "demo"
        if raw in {"prod", "production"}:
            return "production"
        if raw in {"test", "testing"}:
            return "test"
        return raw

    @property
    def resolved_database_url(self) -> str:
        url = self.database_url
        # Vercel functions can only write /tmp. A relative sqlite path is read-only
        # and crashes every request with FUNCTION_INVOCATION_FAILED.
        if os.environ.get("VERCEL") and "postgres" not in url:
            return "sqlite+aiosqlite:////tmp/termpilot.db"
        return url

    @property
    def on_vercel(self) -> bool:
        return bool(os.environ.get("VERCEL"))

    @property
    def strict_auth(self) -> bool:
        return self.env == "production"

    @property
    def codes_required(self) -> bool:
        if not self.require_verification:
            return False
        return bool(self.resend_api_key) or self.env == "test" or bool(
            os.environ.get("PYTEST_CURRENT_TEST")
        )

    @field_validator(
        "xai_api_key",
        "openrouter_api_key",
        "access_code",
        "now_override",
        "linkedin_client_id",
        "linkedin_client_secret",
        "orcid_client_id",
        "orcid_client_secret",
        "x_client_id",
        "x_client_secret",
        "notion_client_id",
        "notion_client_secret",
        "slack_client_id",
        "slack_client_secret",
        "google_client_id",
        "google_client_secret",
        "microsoft_client_id",
        "microsoft_client_secret",
        "canvas_client_id",
        "canvas_client_secret",
        "github_client_id",
        "github_client_secret",
        "jira_client_id",
        "jira_client_secret",
        "discord_client_id",
        "discord_client_secret",
        "resend_api_key",
        "smtp_url",
        "twilio_account_sid",
        "twilio_auth_token",
        "twilio_from",
        mode="before",
    )
    @classmethod
    def empty_key_to_none(cls, value: object) -> object:
        if value == "":
            return None
        return value

    @field_validator("require_verification", mode="before")
    @classmethod
    def blank_bool_false(cls, value: object) -> object:
        if value in {"", None}:
            return False
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return value

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @property
    def frozen_now(self) -> datetime | None:
        if self.env == "production" and not self.now_override:
            return None
        if not self.now_override:
            return None
        return datetime.fromisoformat(self.now_override)

    @property
    def use_live_grok(self) -> bool:
        if self.grok_mode == "fake":
            return False
        if self.grok_mode == "live":
            return True
        return bool(self.xai_api_key)

    @property
    def grok_connection_state(self) -> str:
        if self.simulate_offline:
            return "offline"
        if self.use_live_grok:
            return "live"
        return "fake"

    @property
    def cors_origins(self) -> list[str]:
        origins = [
            self.frontend_origin,
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
            "http://localhost:8000",
            "https://termpilot.org",
            "https://www.termpilot.org",
        ]
        for item in self.cors_origins_extra.split(","):
            cleaned = item.strip()
            if cleaned:
                origins.append(cleaned)
        return list(dict.fromkeys(origins))


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
