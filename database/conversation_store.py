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


class ConversationStore:
    """
    Firestore-based conversation storage for training data collection

    Stores conversations in a structured format optimized for:
    - Model training and fine-tuning
    - Conversation analysis and research
    - User behavior tracking
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        collection_name: str = 'conversations',
        credentials_path: Optional[str] = None
    ):
        """
        Initialize Firestore conversation store

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

        logging.info(f"Firestore conversation store initialized: {collection_name}")

    def _convert_timestamps(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Firestore timestamps to ISO format strings

        Args:
            data: Dictionary potentially containing timestamp fields

        Returns:
            Dictionary with timestamps converted to ISO strings
        """
        for field in ['created_at', 'updated_at']:
            if field in data and hasattr(data[field], 'isoformat'):
                data[field] = data[field].isoformat()
        return data

    async def create_conversation(
        self,
        session_id: str,
        conversation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new conversation record

        Args:
            session_id: Session identifier (used as document ID)
            conversation_data: Complete conversation data including:
                - user_type: Inferred user type
                - conversation_history: List of messages
                - metadata: Session metadata
                - preferences: User preferences

        Returns:
            Created conversation data with timestamps
        """
        conversation_data['session_id'] = session_id
        conversation_data['created_at'] = firestore.SERVER_TIMESTAMP
        conversation_data['updated_at'] = firestore.SERVER_TIMESTAMP

        # Store in Firestore
        self.collection.document(session_id).set(conversation_data)

        # Return with actual timestamps
        conversation_data['created_at'] = datetime.now().isoformat()
        conversation_data['updated_at'] = datetime.now().isoformat()

        logging.info(f"Created conversation: {session_id}")
        return conversation_data

    async def get_conversation(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a conversation by session ID

        Args:
            session_id: Session identifier

        Returns:
            Conversation data or None if not found
        """
        doc = self.collection.document(session_id).get()

        if not doc.exists:
            return None

        conversation_data = doc.to_dict()
        return self._convert_timestamps(conversation_data)

    async def update_conversation(
        self,
        session_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update conversation data (typically to add new messages)

        Args:
            session_id: Session identifier
            updates: Partial update data (e.g., new messages, updated metadata)

        Returns:
            True if successful, False otherwise
        """
        try:
            updates['updated_at'] = firestore.SERVER_TIMESTAMP
            self.collection.document(session_id).update(updates)
            logging.info(f"Updated conversation: {session_id}")
            return True
        except Exception as e:
            logging.error(f"Error updating conversation {session_id}: {e}")
            return False

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get conversation statistics

        Returns:
            Dictionary with various statistics
        """
        docs = self.collection.stream()

        total = 0
        user_types = {}
        total_messages = 0
        intents = {}

        for doc in docs:
            data = doc.to_dict()
            total += 1

            # Count by user type
            user_type = data.get('user_type', 'unknown')
            user_types[user_type] = user_types.get(user_type, 0) + 1

            # Count messages
            history = data.get('conversation_history', [])
            total_messages += len(history)

            # Count intents
            metadata = data.get('metadata', {})
            for intent in metadata.get('intents', []):
                intents[intent] = intents.get(intent, 0) + 1

        return {
            'total_conversations': total,
            'user_type_distribution': user_types,
            'total_messages': total_messages,
            'average_messages_per_conversation': total_messages / total if total > 0 else 0,
            'intent_distribution': intents
        }

    async def export_for_training(
        self,
        output_format: str = 'jsonl',
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10000
    ) -> List[Dict[str, Any]]:
        """
        Export conversations in training-ready format

        Args:
            output_format: 'jsonl', 'qa_pairs', or 'full'
            filters: Optional filters to apply
            limit: Maximum conversations to export

        Returns:
            List of formatted conversation data
        """
        from utils.training_data_export import export_session_for_training

        # Get conversations with optional filters
        query = self.collection.order_by('created_at', direction=firestore.Query.DESCENDING)

        if filters:
            from google.cloud.firestore_v1.base_query import FieldFilter
            for field, value in filters.items():
                query = query.where(filter=FieldFilter(field, '==', value))

        docs = query.limit(limit).stream()

        exported = []
        for doc in docs:
            conv = doc.to_dict()
            conv = self._convert_timestamps(conv)
            formatted = export_session_for_training(conv, format=output_format)
            exported.append(formatted)

        return exported
