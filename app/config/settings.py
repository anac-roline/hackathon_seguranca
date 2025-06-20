import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(".env")) if Path(".env").exists() else None,
        env_file_encoding='utf-8'
    )

    OPENAPI_API_KEY: str = os.getenv("OPENAPI_API_KEY")