"""Configuration management for CRS Chatbot"""
import os
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""

    # Application
    app_name: str = "Sustainable Tourism CRS"
    debug: bool = True

    # Firebase/Firestore — set USE_FIRESTORE=true to enable (default off for HF Spaces)
    use_firestore: bool = False
    firebase_project_name: Optional[str] = None
    firebase_project_id: Optional[str] = None
    firebase_project_number: Optional[str] = None
    firebase_google_application_credentials: Optional[str] = None

    # Google Cloud (fallback)
    google_cloud_project: Optional[str] = None

    # Model Settings
    default_model: str = "gemini-2.5-flash-exp"

    # Model provider: "gemma" (HF Inference, free) or "gemini" (Google API, user key)
    default_model_provider: str = "gemma"

    # HuggingFace (Gemma path) — set HF_TOKEN in env/secrets, never hard-code
    hf_token: Optional[str] = None
    hf_gemma_model: str = "google/gemma-3-27b-it"

    # HuggingFace Dataset repo for conversation persistence (optional free alternative to Firestore)
    # Format: "your-username/your-dataset-repo"  (private repos are fine)
    hf_dataset_repo: Optional[str] = None

    # Chainlit
    chainlit_auth_secret: str = "change-this-secret"

    # Orchestrator
    session_timeout: int = 3600
    max_conversation_history: int = 20

    # Backend API — defaults to same port as the server so HF Spaces works automatically
    backend_api_url: Optional[str] = None
    backend_api_url_fallback: str = "https://adk-agent-service-778145853986.europe-west1.run.app"
    backend_connection_timeout: float = 5.0

    @field_validator("backend_api_url", mode="before")
    @classmethod
    def _set_backend_url(cls, v: Optional[str]) -> str:
        if v:
            return v
        port = os.getenv("PORT", "8001")
        return f"http://localhost:{port}"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"


settings = Settings()
