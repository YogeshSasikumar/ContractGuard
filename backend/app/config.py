import os
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # API Keys
    gemini_api_key: str = ""
    
    # Deployment mode: "full" = load all ML models, "lite" = keyword + Gemini only
    deployment_mode: str = "full"
    
    # Paths
    base_dir: Path = Path(__file__).resolve().parent.parent
    upload_dir: Path = Path(__file__).resolve().parent.parent / "uploads"
    model_path: Path = Path(__file__).resolve().parent.parent / "training" / "models" / "legal-bert-lora"
    data_dir: Path = Path(__file__).resolve().parent / "data"
    
    # Model settings
    use_trained_model: bool = False  # False = rule-based, True = Legal-BERT
    max_seq_length: int = 256
    
    # Server
    port: int = 8000
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]
    # Extra CORS origin for deployed frontend (e.g. https://riskora.vercel.app)
    frontend_url: str = ""
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def is_lite_mode(self) -> bool:
        return self.deployment_mode.lower() == "lite"

    @property
    def all_cors_origins(self) -> list[str]:
        origins = list(self.cors_origins)
        if self.frontend_url:
            origins.append(self.frontend_url)
        return origins

settings = Settings()

# Ensure directories exist
settings.upload_dir.mkdir(parents=True, exist_ok=True)
