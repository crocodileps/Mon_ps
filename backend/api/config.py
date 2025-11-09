"""
Configuration de l'API FastAPI
"""
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Configuration de l'application"""
    
    # Application
    APP_NAME: str = "Mon_PS API"
    APP_VERSION: str = "1.0.0"
    ENV: str = os.getenv("ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Database
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "monps_prod")
    DB_USER: str = os.getenv("DB_USER", "monps_user")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    
    # API Keys
    THE_ODDS_API_KEY: str = os.getenv("THE_ODDS_API_KEY", "")
    
    # CORS
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8001",
    ]
    
    @property
    def database_url(self) -> str:
        """URL de connexion PostgreSQL"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignorer les champs supplémentaires

settings = Settings()
