"""
Conversation Store for Firestore
Stores complete conversations in JSON format for training and analysis
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

try:
    from google.cloud import firestore
    FIRESTORE_AVAILABLE = True
except ImportError:
    FIRESTORE_AVAILABLE = False
    logging.warning("Firestore SDK not installed. Run: pip install google-cloud-firestore")

from .base_store import BaseFirestoreStore


class ConversationStore(BaseFirestoreStore):
    """
    Firestore-based conversation storage for training data collection

    Stores conversations in a structured format optimized for:
    - Model training and fine-tuning
    - Conversation analysis and research
    """

    async def create_conversation(
        self,
        session_id: str,
        conversation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new conversation record

        Args:
            session_id: Session identifier (used as document ID)
            conversation_data: Complete conversation data

        Returns:
            Created conversation data with timestamps
        """
        conversation_data['session_id'] = session_id
        conversation_data['created_at'] = firestore.SERVER_TIMESTAMP
        conversation_data['updated_at'] = firestore.SERVER_TIMESTAMP

        self.collection.document(session_id).set(conversation_data)

        # Return with ISO timestamps
        now = datetime.now().isoformat()
        conversation_data['created_at'] = now
        conversation_data['updated_at'] = now

        logging.info(f"Created conversation: {session_id}")
        return conversation_data

    async def get_conversation(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a conversation by session ID"""
        doc = self.collection.document(session_id).get()

        if not doc.exists:
            return None

        return self._convert_timestamps(doc.to_dict())

    async def update_conversation(
        self,
        session_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update conversation data"""
        try:
            updates['updated_at'] = firestore.SERVER_TIMESTAMP
            self.collection.document(session_id).update(updates)
            logging.info(f"Updated conversation: {session_id}")
            return True
        except Exception as e:
            logging.error(f"Error updating conversation {session_id}: {e}")
            return False

    async def export_for_training(
        self,
        output_format: str = 'full',
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10000
    ) -> List[Dict[str, Any]]:
        """
        Export conversations for training

        Args:
            output_format: Export format ('full' by default)
            filters: Optional filters to apply
            limit: Maximum conversations to export

        Returns:
            List of conversation data
        """
        query = self.collection.order_by('created_at', direction=firestore.Query.DESCENDING)

        if filters:
            from google.cloud.firestore_v1.base_query import FieldFilter
            for field, value in filters.items():
                query = query.where(filter=FieldFilter(field, '==', value))

        docs = query.limit(limit).stream()
        return [self._convert_timestamps(doc.to_dict()) for doc in docs]
