"""
Conversation Store for Firestore
Stores complete conversations in JSON format for training and analysis
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


class ConversationStore:
    """
    Firestore-based conversation storage for training data collection
    
    Stores conversations in a structured format optimized for:
    - Model training and fine-tuning
    - Conversation analysis and research
    - User behavior tracking
    - Export to various training formats
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
        
        # Convert Firestore timestamps to ISO format
        if 'created_at' in conversation_data and hasattr(conversation_data['created_at'], 'isoformat'):
            conversation_data['created_at'] = conversation_data['created_at'].isoformat()
        if 'updated_at' in conversation_data and hasattr(conversation_data['updated_at'], 'isoformat'):
            conversation_data['updated_at'] = conversation_data['updated_at'].isoformat()
        
        return conversation_data
    
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
    
    async def append_message(
        self,
        session_id: str,
        message: Dict[str, Any]
    ) -> bool:
        """
        Append a single message to conversation history
        
        Args:
            session_id: Session identifier
            message: Message data with role, content, timestamp, metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.collection.document(session_id).update({
                'conversation_history': firestore.ArrayUnion([message]),
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            logging.info(f"Appended message to conversation: {session_id}")
            return True
        except Exception as e:
            logging.error(f"Error appending message to {session_id}: {e}")
            return False
    
    async def delete_conversation(self, session_id: str) -> bool:
        """
        Delete a conversation permanently
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if deleted, False if not found
        """
        try:
            self.collection.document(session_id).delete()
            logging.info(f"Deleted conversation: {session_id}")
            return True
        except Exception as e:
            logging.error(f"Error deleting conversation {session_id}: {e}")
            return False
    
    async def list_conversations(
        self,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        List conversations with optional filtering
        
        Args:
            limit: Maximum number of conversations to return
            offset: Number of conversations to skip
            filters: Optional filters (e.g., {'user_type': 'sustainability_focused'})
            
        Returns:
            List of conversation data
        """
        query = self.collection.order_by('created_at', direction=firestore.Query.DESCENDING)
        
        # Apply filters
        if filters:
            for field, value in filters.items():
                query = query.where(filter=FieldFilter(field, '==', value))
        
        if offset > 0:
            query = query.offset(offset)
        
        docs = query.limit(limit).stream()
        
        conversations = []
        for doc in docs:
            conversation_data = doc.to_dict()
            
            # Convert timestamps
            if 'created_at' in conversation_data and hasattr(conversation_data['created_at'], 'isoformat'):
                conversation_data['created_at'] = conversation_data['created_at'].isoformat()
            if 'updated_at' in conversation_data and hasattr(conversation_data['updated_at'], 'isoformat'):
                conversation_data['updated_at'] = conversation_data['updated_at'].isoformat()
            
            conversations.append(conversation_data)
        
        return conversations
    
    async def get_conversations_by_user_type(
        self,
        user_type: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all conversations for a specific user type
        
        Args:
            user_type: User type to filter by
            limit: Maximum number of conversations
            
        Returns:
            List of conversations
        """
        return await self.list_conversations(
            limit=limit,
            filters={'user_type': user_type}
        )
    
    async def get_conversations_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Get conversations within a date range
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            limit: Maximum number of conversations
            
        Returns:
            List of conversations
        """
        query = self.collection.where(
            filter=FieldFilter('created_at', '>=', start_date)
        ).where(
            filter=FieldFilter('created_at', '<=', end_date)
        ).order_by('created_at').limit(limit)
        
        docs = query.stream()
        
        conversations = []
        for doc in docs:
            conversation_data = doc.to_dict()
            
            # Convert timestamps
            if 'created_at' in conversation_data and hasattr(conversation_data['created_at'], 'isoformat'):
                conversation_data['created_at'] = conversation_data['created_at'].isoformat()
            if 'updated_at' in conversation_data and hasattr(conversation_data['updated_at'], 'isoformat'):
                conversation_data['updated_at'] = conversation_data['updated_at'].isoformat()
            
            conversations.append(conversation_data)
        
        return conversations
    
    async def count_conversations(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count total conversations (optionally filtered)
        
        Args:
            filters: Optional filters
            
        Returns:
            Total count
        """
        query = self.collection
        
        if filters:
            for field, value in filters.items():
                query = query.where(filter=FieldFilter(field, '==', value))
        
        docs = query.stream()
        return sum(1 for _ in docs)
    
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
        
        conversations = await self.list_conversations(limit=limit, filters=filters)
        
        exported = []
        for conv in conversations:
            formatted = export_session_for_training(conv, format=output_format)
            exported.append(formatted)
        
        return exported
    
    async def cleanup_old_conversations(self, days_old: int = 90) -> int:
        """
        Remove conversations older than specified days
        
        Args:
            days_old: Age threshold in days
            
        Returns:
            Number of conversations deleted
        """
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        query = self.collection.where(
            filter=FieldFilter('created_at', '<', cutoff_date)
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
        
        logging.info(f"Cleaned up {count} old conversations (>{days_old} days)")
        return count
    
    async def backup_conversations(
        self,
        backup_collection: str = 'conversations_backup'
    ) -> int:
        """
        Backup all conversations to another collection
        
        Args:
            backup_collection: Name of backup collection
            
        Returns:
            Number of conversations backed up
        """
        docs = self.collection.stream()
        backup_col = self.db.collection(backup_collection)
        
        count = 0
        batch = self.db.batch()
        
        for doc in docs:
            backup_doc = backup_col.document(doc.id)
            batch.set(backup_doc, doc.to_dict())
            count += 1
            
            if count % 500 == 0:
                batch.commit()
                batch = self.db.batch()
        
        if count % 500 != 0:
            batch.commit()
        
        logging.info(f"Backed up {count} conversations to {backup_collection}")
        return count
