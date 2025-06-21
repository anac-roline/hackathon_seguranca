import os
from pathlib import Path
from typing import ClassVar, List, Dict

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(".env")) if Path(".env").exists() else None,
        env_file_encoding='utf-8'
    )

    OPENAPI_API_KEY: str = os.getenv("OPENAPI_API_KEY")
    
    # lista com as empresas que podem ser analisadas com o id e nome
    COMPANIES: ClassVar[List[Dict[str, str]]] = [
        {"id": 1, "name": "terracap"},
        {"id": 2, "name": "Neoenergia"},
        {"id": 3, "name": "SLU"},
        {"id": 4, "name": "Caesb"},
    ]