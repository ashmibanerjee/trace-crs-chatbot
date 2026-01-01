"""
Base Firestore Store
Shared functionality for all Firestore-based stores
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


class BaseFirestoreStore:
    """
    Base class for Firestore stores with common functionality
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        collection_name: str = 'base_collection',
        credentials_path: Optional[str] = None
    ):
        """
        Initialize Firestore store

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
            self.db = firestore.Client(project=project_id)

        self.collection_name = collection_name
        self.collection = self.db.collection(collection_name)

        logging.info(f"Firestore store initialized: {collection_name}")

    def _convert_timestamps(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Firestore timestamps to ISO format strings

        Args:
            data: Dictionary potentially containing timestamp fields

        Returns:
            Dictionary with timestamps converted to ISO strings
        """
        for field in ['created_at', 'updated_at', 'last_activity']:
            if field in data and hasattr(data[field], 'isoformat'):
                data[field] = data[field].isoformat()
        return data
