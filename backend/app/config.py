from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "SE Product Assistant API"
    database_url: str = "sqlite:///./se_product_assistant.db"
    cors_origins: str = "http://localhost:5173"
    demo_username: str = ""
    demo_password: str = ""
    # Fraction of /api/match requests checked in the background against an
    # exhaustive scan. Keep 0 in normal production; use e.g. 0.02 during
    # validation to sample 2% without slowing customer responses.
    match_quality_guard_sample_rate: float = 0.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
