from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="COINER_", env_file=".env", extra="ignore")

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    catalog_path: Path = Path("data/catalog.jsonl")
    max_image_bytes: int = 10 * 1024 * 1024


settings = Settings()
