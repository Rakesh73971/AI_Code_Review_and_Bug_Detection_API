from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_hostname: str
    database_port: str
    database_password: str
    database_name: str
    database_username: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    google_api_key: str
    github_token: Optional[str] = None
    gemini_model: str = "gemini-2.5-flash"

    gemini_embedding_model: str = "models/gemini-embedding-001"
    chroma_persist_dir: str = "./chroma_data"



    docs_collection_name: str = "official_docs"

settings = Settings()