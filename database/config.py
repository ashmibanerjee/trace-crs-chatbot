"""
Database Configuration
Factory functions for creating database stores using centralized config
"""
from typing import Optional

from .session_store import SessionStore
from .firestore_store import FirestoreSessionStore


def get_session_store(backend: Optional[str] = None) -> SessionStore:
    """
    Factory function to create Firestore session store
    Reads credentials from main config
    
    Returns:
        FirestoreSessionStore instance configured from settings
    """
    from config import settings
    
    project_id = settings.firebase_project_id or settings.google_cloud_project
    credentials_path = settings.firebase_google_application_credentials
    
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
    credentials_path = settings.firebase_google_application_credentials
    
    if not project_id:
        raise ValueError(
            "FIREBASE_PROJECT_ID or GOOGLE_CLOUD_PROJECT must be set in .env file"
        )
    
    return ConversationStore(
        project_id=project_id,
        credentials_path=credentials_path,
        collection_name='conversations'
    )
