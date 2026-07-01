"""
Centralized Configuration
==========================
All JARVIS OS settings in one Pydantic v2 model.
Loaded from: .env file → environment variables → YAML config → defaults

Usage:
    settings = Settings()
    print(settings.ai.provider)      # "claude"
    print(settings.voice.wake_word)  # "jarvis"
    print(settings.security.safe_mode)  # True

    # Reload from environment
    settings = Settings(_env_file=".env.production")
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------------
# Sub-settings models
# ---------------------------------------------------------------------------


class AISettings(BaseSettings):
    """AI provider configuration."""
    model_config = SettingsConfigDict(env_prefix="JARVIS_AI_", extra="ignore")

    provider: str = Field("claude", description="AI provider: claude|openai|gemini|local")
    claude_model: str = Field("claude-opus-4-5")
    openai_model: str = Field("gpt-4o")
    gemini_model: str = Field("gemini-1.5-pro")
    local_model_path: str = Field("./data/models/model.gguf")
    max_tokens: int = Field(4096, ge=1, le=128000)
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    timeout_seconds: int = Field(60, ge=1)
    max_context_tokens: int = Field(80000, ge=1000)

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        allowed = {"claude", "openai", "gemini", "local"}
        if v not in allowed:
            raise ValueError(f"AI provider must be one of: {allowed}")
        return v


class VoiceSettings(BaseSettings):
    """Voice pipeline configuration."""
    model_config = SettingsConfigDict(env_prefix="JARVIS_VOICE_", extra="ignore")

    enabled: bool = Field(True)
    wake_word: str = Field("jarvis")
    wake_word_sensitivity: float = Field(0.5, ge=0.0, le=1.0)
    input_device: str | None = Field(None)
    output_device: str | None = Field(None)
    stt_provider: str = Field("faster-whisper")
    stt_model_size: str = Field("base.en")
    tts_provider: str = Field("pyttsx3")
    tts_voice: str = Field("")
    audio_sample_rate: int = Field(16000)
    noise_reduction: bool = Field(True)
    latency_target_ms: int = Field(200)


class MemorySettings(BaseSettings):
    """Memory system configuration."""
    model_config = SettingsConfigDict(env_prefix="JARVIS_MEMORY_", extra="ignore")

    enabled: bool = Field(True)
    short_term_limit: int = Field(50, ge=5, le=500)
    long_term_db_path: str = Field("./data/memory/long_term/jarvis.db")
    conversations_db_path: str = Field("./data/memory/long_term/conversations.db")
    vector_store_path: str = Field("./data/memory/vector_store")
    embedding_model: str = Field("all-MiniLM-L6-v2")
    retention_days: int = Field(365, ge=1)


class SecuritySettings(BaseSettings):
    """Security and permission configuration."""
    model_config = SettingsConfigDict(env_prefix="JARVIS_SECURITY_", extra="ignore")

    require_confirmation: bool = Field(True)
    safe_mode: bool = Field(True)
    audit_log_path: str = Field("./data/audit/audit.jsonl")
    allowed_paths: list[str] = Field(
        default_factory=lambda: ["~/Documents", "~/Downloads", "~/Desktop"]
    )
    forbidden_paths: list[str] = Field(
        default_factory=lambda: ["/System", "/Library", "/usr", "/etc"]
    )
    keyring_service: str = Field("jarvis-os")


class DesktopSettings(BaseSettings):
    """Desktop automation configuration."""
    model_config = SettingsConfigDict(env_prefix="JARVIS_DESKTOP_", extra="ignore")

    enabled: bool = Field(True)
    keyboard_delay_ms: float = Field(50.0, ge=0.0)


class BrowserSettings(BaseSettings):
    """Browser automation configuration."""
    model_config = SettingsConfigDict(env_prefix="JARVIS_BROWSER_", extra="ignore")

    enabled: bool = Field(True)
    default_browser: str = Field("chromium")
    headless: bool = Field(False)
    timeout_ms: int = Field(30000)


class UISettings(BaseSettings):
    """UI configuration."""
    model_config = SettingsConfigDict(env_prefix="JARVIS_UI_", extra="ignore")

    theme: str = Field("dark")
    accent_color: str = Field("#7C3AED")
    window_opacity: float = Field(0.97, ge=0.1, le=1.0)
    always_on_top: bool = Field(False)
    start_minimized: bool = Field(False)


class PluginSettings(BaseSettings):
    """Plugin system configuration."""
    model_config = SettingsConfigDict(env_prefix="JARVIS_PLUGINS_", extra="ignore")

    enabled: bool = Field(True)
    plugins_dir: str = Field("./plugins")
    auto_load: bool = Field(True)


# ---------------------------------------------------------------------------
# Main Settings
# ---------------------------------------------------------------------------


class Settings(BaseSettings):
    """
    JARVIS OS global settings.
    Reads from .env file and environment variables.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="JARVIS_",
        extra="ignore",
        case_sensitive=False,
    )

    # Core
    environment: str = Field("development", alias="JARVIS_ENV")
    log_level: str = Field("INFO", alias="JARVIS_LOG_LEVEL")
    log_file: str = Field("./data/logs/jarvis.log", alias="JARVIS_LOG_FILE")
    log_rotation: str = Field("10 MB", alias="JARVIS_LOG_ROTATION")
    log_retention: str = Field("30 days", alias="JARVIS_LOG_RETENTION")
    log_format: str = Field("pretty", alias="JARVIS_LOG_FORMAT")
    data_dir: str = Field("./data", alias="JARVIS_DATA_DIR")
    max_concurrent_tasks: int = Field(5, alias="JARVIS_MAX_CONCURRENT_TASKS")

    # Sub-configurations (nested, loaded from same env)
    ai: AISettings = Field(default_factory=AISettings)
    voice: VoiceSettings = Field(default_factory=VoiceSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    desktop: DesktopSettings = Field(default_factory=DesktopSettings)
    browser: BrowserSettings = Field(default_factory=BrowserSettings)
    ui: UISettings = Field(default_factory=UISettings)
    plugins: PluginSettings = Field(default_factory=PluginSettings)

    @field_validator("environment")
    @classmethod
    def validate_env(cls, v: str) -> str:
        allowed = {"development", "production", "testing"}
        if v not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    def ensure_directories(self) -> None:
        """Create all necessary data directories."""
        dirs = [
            self.data_dir,
            Path(self.log_file).parent,
            Path(self.memory.long_term_db_path).parent,
            self.memory.vector_store_path,
            Path(self.security.audit_log_path).parent,
            self.plugins.plugins_dir,
        ]
        for d in dirs:
            Path(d).mkdir(parents=True, exist_ok=True)
