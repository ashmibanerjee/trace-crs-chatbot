"""
Database Configuration
Factory functions for creating database stores using centralized config
"""
from typing import Optional
import os
from pathlib import Path

from .session_store import SessionStore
from .firestore_store import FirestoreSessionStore


def _resolve_credentials_path(credentials_path: Optional[str]) -> Optional[str]:
    """
    Resolve credentials path to absolute path from project root
    
    Args:
        credentials_path: Path from settings (can be relative or absolute)
        
    Returns:
        Absolute path or None
    """
    if not credentials_path:
        return None
    
    # If already absolute, return as-is
    if os.path.isabs(credentials_path):
        return credentials_path
    
    # Get project root (parent of database directory)
    project_root = Path(__file__).parent.parent
    
    # Resolve relative path from project root
    abs_path = str(project_root / credentials_path)
    
    print(f"[Config] Resolved credentials path: {abs_path}")
    print(f"[Config] Credentials file exists: {os.path.exists(abs_path)}")
    
    return abs_path


def get_session_store(backend: Optional[str] = None) -> SessionStore:
    """
    Factory function to create Firestore session store
    Reads credentials from main config
    
    Returns:
        FirestoreSessionStore instance configured from settings
    """
    from config import settings
    
    project_id = settings.firebase_project_id or settings.google_cloud_project
    credentials_path = _resolve_credentials_path(settings.firebase_google_application_credentials)
    
    if not project_id:
        raise ValueError(
            "FIREBASE_PROJECT_ID or GOOGLE_CLOUD_PROJECT must be set in .env file"
        )
    
    return FirestoreSessionStore(
        project_id=project_id,
        credentials_path=credentials_path,
        collection_name='sessions'
    )


def get_conversation_store():
    """
    Factory function to create Firestore conversation store
    Reads credentials from main config
    
    Returns:
        ConversationStore instance configured from settings
    """
    from .conversation_store import ConversationStore
    from config import settings
    
    project_id = settings.firebase_project_id or settings.google_cloud_project
    credentials_path = _resolve_credentials_path(settings.firebase_google_application_credentials)
    
    if not project_id:
        raise ValueError(
            "FIREBASE_PROJECT_ID or GOOGLE_CLOUD_PROJECT must be set in .env file"
        )
    
    return ConversationStore(
        project_id=project_id,
        credentials_path=credentials_path,
        collection_name='conversations'
    )
