"""
Firestore Session Store Implementation
Production-ready session storage using Google Cloud Firestore
"""
from typing import Dict, Any, Optional
from datetime import datetime
import logging

try:
    from google.cloud import firestore
    FIRESTORE_AVAILABLE = True
except ImportError:
    FIRESTORE_AVAILABLE = False
    logging.warning("Firestore SDK not installed. Run: pip install google-cloud-firestore")

from .session_store import SessionStore
from .base_store import BaseFirestoreStore


class FirestoreSessionStore(BaseFirestoreStore, SessionStore):
    """
    Firestore-based session storage for production use

    Features:
    - Persistent storage
    - Real-time updates
    - Automatic indexing
    - Scalable to millions of sessions
    """
    
    async def create_session(self, session_id: str, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new session in Firestore"""
        session_data['id'] = session_id
        session_data['created_at'] = firestore.SERVER_TIMESTAMP
        session_data['last_activity'] = firestore.SERVER_TIMESTAMP

        self.collection.document(session_id).set(session_data)

        # Return with ISO timestamps
        now = datetime.now().isoformat()
        session_data['created_at'] = now
        session_data['last_activity'] = now

        return session_data
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session from Firestore"""
        doc = self.collection.document(session_id).get()

        if not doc.exists:
            return None

        session_data = doc.to_dict()
        return self._convert_timestamps(session_data)
    
    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """Update session in Firestore"""
        try:
            updates['last_activity'] = firestore.SERVER_TIMESTAMP
            self.collection.document(session_id).update(updates)
            return True
        except Exception as e:
            logging.error(f"Error updating session {session_id}: {e}")
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session from Firestore"""
        try:
            self.collection.document(session_id).delete()
            return True
        except Exception as e:
            logging.error(f"Error deleting session {session_id}: {e}")
            return False
