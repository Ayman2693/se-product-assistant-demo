from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "SE Product Assistant API"
    database_url: str = "sqlite:///./se_product_assistant.db"
    cors_origins: str = "http://localhost:5173"
    demo_username: str = ""
    demo_password: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
