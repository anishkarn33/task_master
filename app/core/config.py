from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://username:password@localhost:5432/taskmaster"
    
    # Security
    SECRET_KEY: str = "your-super-secret-key-here-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # Project info
    PROJECT_NAME: str = "TaskMaster API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "A comprehensive task management API"

    #llama configuration
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    LLAMA_MODEL: str = os.getenv("LLAMA_MODEL", "llama2")
    AI_TEMPERATURE: float = float(os.getenv("AI_TEMPERATURE", "0.3"))
    
    # Enable/disable AI features
    AI_ENABLED: bool = os.getenv("AI_ENABLED", "true").lower() == "true"
    AI_CHAT_ENABLED: bool = os.getenv("AI_CHAT_ENABLED", "true").lower() == "true"
    AI_SUGGESTIONS_ENABLED: bool = os.getenv("AI_SUGGESTIONS_ENABLED", "true").lower() == "true"
    AI_AUTO_ASSIGNMENT_ENABLED: bool = os.getenv("AI_AUTO_ASSIGNMENT_ENABLED", "true").lower() == "true"

    class Config:
        env_file = ".env"


settings = Settings()