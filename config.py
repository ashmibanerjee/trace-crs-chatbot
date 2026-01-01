"""Configuration management for CRS Chatbot"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    app_name: str = "Sustainable Tourism CRS"
    debug: bool = True
    
    # Firebase/Firestore
    firebase_project_name: Optional[str] = None
    firebase_project_id: Optional[str] = None
    firebase_project_number: Optional[str] = None
    firebase_google_application_credentials: Optional[str] = None
    
    # Google Cloud (fallback)
    google_cloud_project: Optional[str] = None
    
    # Model Settings
    default_model: str = "gemini-2.5-flash-exp"
    
    # Chainlit
    chainlit_auth_secret: str = "change-this-secret"
    
    # Orchestrator
    session_timeout: int = 3600
    max_conversation_history: int = 20

    # Backend API
    backend_api_url: str = "http://localhost:8001"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"  # Allow extra fields from .env


settings = Settings()
