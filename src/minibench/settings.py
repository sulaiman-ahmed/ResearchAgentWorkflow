from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql+psycopg://minibench:changeme@db:5432/minibench"

    # Upload storage (inside container)
    upload_dir: str = "/app/uploads"

    # Model provider
    model_mode: str = "fake"  # "fake" | "live"
    model_name: str = ""
    model_api_key: str = ""

    # Local API keys
    reviewer_api_key: str = ""
    worker_api_key: str = ""


settings = Settings()
