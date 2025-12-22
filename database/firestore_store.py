"""
Firestore Session Store Implementation
Production-ready session storage using Google Cloud Firestore
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

try:
    from google.cloud import firestore
    from google.cloud.firestore_v1.base_query import FieldFilter
    FIRESTORE_AVAILABLE = True
except ImportError:
    FIRESTORE_AVAILABLE = False
    logging.warning("Firestore SDK not installed. Run: pip install google-cloud-firestore")

from .session_store import SessionStore


class FirestoreSessionStore(SessionStore):
    """
    Firestore-based session storage for production use
    
    Features:
    - Persistent storage
    - Real-time updates
    - Automatic indexing
    - Scalable to millions of sessions
    - TTL support via Cloud Functions
    
    Setup:
        1. Install: pip install google-cloud-firestore
        2. Set GOOGLE_APPLICATION_CREDENTIALS env variable
        3. Or use Application Default Credentials in GCP
    """
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        collection_name: str = 'sessions',
        credentials_path: Optional[str] = None
    ):
        """
        Initialize Firestore session store
        
        Args:
            project_id: GCP project ID (uses default if None)
            collection_name: Firestore collection name
            credentials_path: Path to service account JSON (optional)
        """
        if not FIRESTORE_AVAILABLE:
            raise ImportError(
                "Firestore SDK not installed. "
                "Install with: pip install google-cloud-firestore"
            )
        
        # Initialize Firestore client
        if credentials_path:
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path
            )
            self.db = firestore.Client(project=project_id, credentials=credentials)
        else:
            # Use Application Default Credentials
            self.db = firestore.Client(project=project_id)
        
        self.collection_name = collection_name
        self.collection = self.db.collection(collection_name)
        
        logging.info(f"Firestore session store initialized: {collection_name}")
    
    async def create_session(self, session_id: str, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new session in Firestore"""
        session_data['id'] = session_id
        session_data['created_at'] = firestore.SERVER_TIMESTAMP
        session_data['last_activity'] = firestore.SERVER_TIMESTAMP
        
        # Store in Firestore
        self.collection.document(session_id).set(session_data)
        
        # Return with actual timestamps
        session_data['created_at'] = datetime.now().isoformat()
        session_data['last_activity'] = datetime.now().isoformat()
        
        return session_data
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session from Firestore"""
        doc = self.collection.document(session_id).get()
        
        if not doc.exists:
            return None
        
        session_data = doc.to_dict()
        
        # Convert Firestore timestamps to ISO format
        if 'created_at' in session_data and hasattr(session_data['created_at'], 'isoformat'):
            session_data['created_at'] = session_data['created_at'].isoformat()
        if 'last_activity' in session_data and hasattr(session_data['last_activity'], 'isoformat'):
            session_data['last_activity'] = session_data['last_activity'].isoformat()
        
        return session_data
    
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
    
    async def list_sessions(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List sessions from Firestore with pagination"""
        query = self.collection.order_by('created_at', direction=firestore.Query.DESCENDING)
        
        if offset > 0:
            query = query.offset(offset)
        
        docs = query.limit(limit).stream()
        
        sessions = []
        for doc in docs:
            session_data = doc.to_dict()
            
            # Convert timestamps
            if 'created_at' in session_data and hasattr(session_data['created_at'], 'isoformat'):
                session_data['created_at'] = session_data['created_at'].isoformat()
            if 'last_activity' in session_data and hasattr(session_data['last_activity'], 'isoformat'):
                session_data['last_activity'] = session_data['last_activity'].isoformat()
            
            sessions.append(session_data)
        
        return sessions
    
    async def cleanup_expired_sessions(self, timeout_seconds: int) -> int:
        """
        Remove expired sessions from Firestore
        
        Note: For production, consider using Cloud Functions with TTL policy
        instead of manual cleanup for better performance.
        """
        cutoff_time = datetime.now() - timedelta(seconds=timeout_seconds)
        
        # Query for expired sessions
        query = self.collection.where(
            filter=FieldFilter('last_activity', '<', cutoff_time)
        )
        
        docs = query.stream()
        
        # Delete in batch
        batch = self.db.batch()
        count = 0
        
        for doc in docs:
            batch.delete(doc.reference)
            count += 1
            
            # Firestore batch limit is 500
            if count % 500 == 0:
                batch.commit()
                batch = self.db.batch()
        
        # Commit remaining
        if count % 500 != 0:
            batch.commit()
        
        logging.info(f"Cleaned up {count} expired sessions")
        return count
    
    def get_session_count(self) -> int:
        """Get total number of sessions (useful for monitoring)"""
        # Note: This is an expensive operation in Firestore
        # Consider using a counter document in production
        docs = self.collection.stream()
        return sum(1 for _ in docs)
    
    def get_active_sessions_count(self, timeout_seconds: int = 3600) -> int:
        """Get count of active sessions (last hour by default)"""
        cutoff_time = datetime.now() - timedelta(seconds=timeout_seconds)
        
        query = self.collection.where(
            filter=FieldFilter('last_activity', '>=', cutoff_time)
        )
        
        docs = query.stream()
        return sum(1 for _ in docs)
