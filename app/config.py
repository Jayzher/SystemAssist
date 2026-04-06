from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "ai_log_system"
    api_key: str = "change-me-to-a-strong-api-key"
    llama_model_dir: str = str(
        Path(__file__).resolve().parent.parent.parent / "Llama-3.2-3B"
    )
    gguf_model_path: str = str(
        Path(__file__).resolve().parent.parent.parent / "Llama-3.2-3B" / "Llama-3.2-3B-Instruct-Q4_K_M.gguf"
    )
    embedding_model: str = "all-MiniLM-L6-v2"
    faiss_index_path: str = str(
        Path(__file__).resolve().parent.parent / "data" / "faiss_index"
    )
    session_ttl_hours: int = 24
    user_session_ttl_minutes: int = 30

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
