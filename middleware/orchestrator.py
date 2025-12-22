"""
Orchestrator Middleware
Connects Chainlit frontend to backend agents
"""
from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime
from config import settings
from backend import MinimalBackend, AgentResponse
from database.config import get_session_store, get_conversation_store


class UIElement:
    """Represents a UI element for Chainlit"""
    
    def __init__(self, element_type: str, data: Dict[str, Any]):
        self.type = element_type
        self.data = data
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.type,
            'data': self.data
        }


class SessionManager:
    """
    Manages user sessions using Firestore storage
    Credentials read from .env file
    """
    
    def __init__(self):
        """
        Initialize session manager with Firestore from .env
        """
        self.store = get_session_store()
        self.timeout = settings.session_timeout
        self.max_history = settings.max_conversation_history
    
    async def get_or_create_session(self, session_id: str) -> Dict[str, Any]:
        """Get existing session or create new one"""
        
        # Try to get existing session
        session = await self.store.get_session(session_id)
        
        if session is None:
            # Create new session
            session_data = {
                'user_type': None,  # Will be inferred by backend
                'user_type_confidence': 0.0,
                'preferences': {
                    'sustainability_weight': 0.8,
                    'budget': {'min': 0, 'max': 10000},
                    'interests': []
                },
                'collected_entities': {},
                'conversation_history': [],  # Training-ready format: [{role, content, timestamp, metadata}]
                'metadata': {
                    'total_turns': 0,
                    'intents': [],
                    'clarification_count': 0
                }
            }
            session = await self.store.create_session(session_id, session_data)
        
        return session
    
    async def update_session(self, session_id: str, updates: Dict[str, Any]):
        """Update session state"""
        await self.store.update_session(session_id, updates)
    
    async def clear_session(self, session_id: str):
        """Clear a session"""
        await self.store.delete_session(session_id)
    
    async def trim_history(self, session_id: str):
        """Trim conversation history to max length"""
        session = await self.store.get_session(session_id)
        if session:
            history = session.get('conversation_history', [])
            if len(history) > self.max_history:
                await self.store.update_session(
                    session_id,
                    {'conversation_history': history[-self.max_history:]}
                )


class ConversationOrchestrator:
    """
    Main orchestrator that connects frontend to backend.
    This is the middleware layer that can be easily extended.
    """
    
    def __init__(self):
        """
        Initialize orchestrator with Firestore storage
        Credentials read from .env file
        """
        self.backend = MinimalBackend()
        self.session_manager = SessionManager()
        
        # Initialize Firestore conversation store from .env
        self.conversation_store = get_conversation_store()
    
    async def process_message(
        self,
        message: str,
        session_id: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main orchestration logic.
        
        Args:
            message: User message text
            session_id: Unique session identifier
            user_context: Additional context from the UI
            
        Returns:
            Dictionary with formatted response for Chainlit
        """
        
        # 1. Get or create session
        session_state = await self.session_manager.get_or_create_session(session_id)
        
        # 2. Merge user context if provided
        if user_context:
            session_state['metadata'].update(user_context)
        
        # 3. Pre-process message
        processed_message = self._preprocess_message(message, session_state)
        
        # 4. Call backend agents
        try:
            agent_response = await self.backend.process_message(
                message=processed_message,
                session_state=session_state
            )
        except Exception as e:
            return self._create_error_response(str(e))
        
        # 5. Post-process for Chainlit UI
        ui_response = self._format_for_chainlit(agent_response, session_state)
        
        # 6. Update session in database
        await self.session_manager.update_session(session_id, session_state)
        await self.session_manager.trim_history(session_id)
        
        # 7. Save conversation to conversation store (for training data)
        await self._save_conversation(session_id, session_state)
        
        return ui_response
    
    def _preprocess_message(
        self,
        message: str,
        session_state: Dict[str, Any]
    ) -> str:
        """Pre-process user message"""
        
        # Clean message
        message = message.strip()
        
        # Add context awareness (future enhancement)
        # For now, just return the message
        return message
    
    def _format_for_chainlit(
        self,
        agent_response: AgentResponse,
        session_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Convert agent response to Chainlit-compatible format.
        This is where we create UI elements.
        """
        
        response = {
            'text': agent_response.text,
            'elements': [],
            'actions': [],
            'metadata': agent_response.metadata
        }
        
        # Add recommendation cards
        if agent_response.recommendations:
            response['elements'].extend(
                self._create_recommendation_cards(agent_response.recommendations)
            )
        
        # Add clarification options
        if agent_response.requires_clarification:
            response['actions'].extend(
                self._create_quick_replies(agent_response.clarification_options)
            )
        
        # Add session info (for debugging)
        if settings.debug:
            response['debug_info'] = {
                'agent_name': agent_response.agent_name,
                'action': agent_response.action,
                'session_entities': session_state.get('collected_entities', {})
            }
        
        return response
    
    def _create_recommendation_cards(
        self,
        recommendations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Create UI cards for recommendations"""
        
        cards = []
        for rec in recommendations:
            card = {
                'type': 'card',
                'data': {
                    'id': rec['id'],
                    'title': rec['name'],
                    'description': rec['description'],
                    'sustainability_score': rec.get('sustainability_score', 0),
                    'carbon_offset': rec.get('carbon_offset', 'N/A'),
                    'certifications': rec.get('certifications', []),
                    'image_url': rec.get('image_url')
                }
            }
            cards.append(card)
        
        return cards
    
    def _create_quick_replies(
        self,
        options: List[str]
    ) -> List[Dict[str, Any]]:
        """Create quick reply buttons"""
        
        actions = []
        for option in options:
            actions.append({
                'type': 'button',
                'data': {
                    'label': option,
                    'value': option
                }
            })
        
        return actions
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create error response"""
        
        return {
            'text': f"⚠️ I encountered an error: {error_message}\n\nPlease try again or rephrase your question.",
            'elements': [],
            'actions': [],
            'metadata': {'error': True}
        }
    
    async def handle_action(
        self,
        action_name: str,
        action_value: Any,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Handle user actions (button clicks, etc.)
        """
        
        session_state = await self.session_manager.get_or_create_session(session_id)
        
        # Handle different action types
        if action_name == "quick_reply":
            # Treat quick reply as a new message
            return await self.process_message(
                message=str(action_value),
                session_id=session_id
            )
        
        elif action_name == "more_info":
            # Request more information about a recommendation
            return {
                'text': f"Here's more information about {action_value}...",
                'elements': [],
                'actions': []
            }
        
        elif action_name == "reset":
            # Reset conversation
            await self.session_manager.clear_session(session_id)
            return {
                'text': "Conversation reset! Let's start fresh. Where would you like to explore?",
                'elements': [],
                'actions': []
            }
        
        else:
            return {
                'text': f"Action '{action_name}' received.",
                'elements': [],
                'actions': []
            }
    
    async def stream_response(
        self,
        message: str,
        session_id: str
    ):
        """
        Stream response tokens (for future streaming support)
        
        Yields:
            Text chunks for streaming display
        """
        
        # For now, just yield the full response
        # Later, this can be enhanced with actual streaming from LLM
        response = await self.process_message(message, session_id)
        
        # Simulate streaming by chunking
        text = response['text']
        chunk_size = 10
        
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i + chunk_size]
            yield chunk
            await asyncio.sleep(0.05)  # Simulate network delay
    
    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information from database"""
        return await self.session_manager.store.get_session(session_id)
    
    async def get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for a session from database"""
        session = await self.session_manager.get_or_create_session(session_id)
        return session.get('conversation_history', [])
    
    async def _save_conversation(self, session_id: str, session_state: Dict[str, Any]):
        """
        Save or update conversation in conversation store for training data
        
        Args:
            session_id: Session identifier
            session_state: Current session state with conversation history
        """
        try:
            # Check if conversation already exists
            existing = await self.conversation_store.get_conversation(session_id)
            
            if existing:
                # Update existing conversation with new messages
                await self.conversation_store.update_conversation(
                    session_id,
                    {
                        'conversation_history': session_state['conversation_history'],
                        'user_type': session_state.get('user_type', 'unknown'),
                        'user_type_confidence': session_state.get('user_type_confidence', 0.0),
                        'metadata': session_state.get('metadata', {})
                    }
                )
            else:
                # Create new conversation record
                conversation_data = {
                    'user_type': session_state.get('user_type', 'unknown'),
                    'user_type_confidence': session_state.get('user_type_confidence', 0.0),
                    'conversation_history': session_state['conversation_history'],
                    'metadata': session_state.get('metadata', {}),
                    'preferences': session_state.get('preferences', {})
                }
                await self.conversation_store.create_conversation(session_id, conversation_data)
                
        except Exception as e:
            # Log error but don't fail the main conversation flow
            import logging
            logging.error(f"Error saving conversation {session_id}: {e}")
    
    async def export_conversations_for_training(
        self,
        output_format: str = 'jsonl',
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10000
    ) -> List[Dict[str, Any]]:
        """
        Export conversations for model training
        
        Args:
            output_format: 'jsonl', 'qa_pairs', or 'full'
            filters: Optional filters (e.g., {'user_type': 'sustainability_focused'})
            limit: Maximum conversations to export
            
        Returns:
            List of formatted conversations
        """
        return await self.conversation_store.export_for_training(
            output_format=output_format,
            filters=filters,
            limit=limit
        )
    
    async def get_conversation_statistics(self) -> Dict[str, Any]:
        """Get statistics about stored conversations"""
        return await self.conversation_store.get_statistics()



# Singleton instance
orchestrator = ConversationOrchestrator()
