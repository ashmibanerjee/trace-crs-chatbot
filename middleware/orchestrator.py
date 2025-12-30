"""
Orchestrator Middleware
Connects Chainlit frontend to backend agents
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx
from config import settings
from database.config import get_session_store, get_conversation_store
from middleware.clarification_handler import ClarificationHandler, ClarificationState


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
        self.session_manager = SessionManager()
        self.clarification_handler = ClarificationHandler()

        # Initialize Firestore conversation store from .env
        self.conversation_store = get_conversation_store()
    
    async def process_message(
        self,
        message: str,
        session_id: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main orchestration logic for processing user messages.
        Currently focused on clarification flow handling.

        Args:
            message: User message text
            session_id: Unique session identifier
            user_context: Additional context from the UI

        Returns:
            Dictionary with formatted response for Chainlit
        """

        # Get or create session
        session_state = await self.session_manager.get_or_create_session(session_id)

        # Merge user context if provided
        if user_context:
            session_state['metadata'].update(user_context)

        # Check if there's an active clarification flow
        if self.is_clarification_active(session_state):
            return await self.handle_clarification_answer(message, session_id)

        # Check if we should trigger clarification questions
        if self.should_trigger_clarification(message, session_state):
            return await self.start_clarification_flow(message, session_id)

        # For non-clarification messages, return a simple acknowledgment
        # TODO: Integrate with backend recommendation agents
        return {
            'text': "Thank you for your message. Recommendation system integration coming soon.",
            'elements': [],
            'actions': [],
            'metadata': {}
        }
    
    def _add_to_history(
        self,
        session_state: Dict[str, Any],
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Helper to add a message to conversation history

        Args:
            session_state: Current session state
            role: 'user' or 'assistant'
            content: Message content
            metadata: Optional metadata for the message
        """
        entry = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        session_state['conversation_history'].append(entry)

    async def _update_and_save_session(
        self,
        session_id: str,
        session_state: Dict[str, Any]
    ):
        """
        Helper to update session and save to conversation store

        Args:
            session_id: Session identifier
            session_state: Current session state
        """
        await self.session_manager.update_session(session_id, session_state)
        await self._save_conversation(session_id, session_state)
    
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

        Args:
            action_name: Type of action
            action_value: Action payload
            session_id: Session identifier

        Returns:
            Response dictionary
        """
        if action_name == "quick_reply":
            # Treat quick reply as a new message
            return await self.process_message(
                message=str(action_value),
                session_id=session_id
            )

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
            
            # Prepare clarification data in ADK format if available
            clarification_data = None
            clarification_complete = session_state.get('clarification_complete', False)

            clarification_state_dict = session_state.get('clarification_state')
            if clarification_state_dict:
                # Convert to ADK format: {query, clarifying_questions: [{id, category, question, answer}], clarification_complete}
                clarification_data = {
                    'query': clarification_state_dict.get('original_query', ''),
                    'clarifying_questions': clarification_state_dict.get('questions', []),
                    'clarification_complete': clarification_complete
                }
            elif session_state.get('clarification_complete'):
                # If clarification is complete, reconstruct from collected answers
                answers = session_state.get('collected_entities', {}).get('clarification_answers', {})
                if answers:
                    # Reconstruct the full structure with answers
                    questions_with_answers = []
                    for q_id_str, ans_data in sorted(answers.items(), key=lambda x: int(x[0])):
                        questions_with_answers.append({
                            'id': int(q_id_str),
                            'category': ans_data.get('category', ''),
                            'question': ans_data.get('question', ''),
                            'answer': ans_data.get('answer', '')
                        })

                    clarification_data = {
                        'query': session_state.get('metadata', {}).get('original_clarification_query', ''),
                        'clarifying_questions': questions_with_answers,
                        'clarification_complete': True
                    }

            update_data = {
                'conversation_history': session_state['conversation_history'],
                'user_type': session_state.get('user_type', 'unknown'),
                'user_type_confidence': session_state.get('user_type_confidence', 0.0),
                'metadata': session_state.get('metadata', {})
            }

            # Add clarification data if available
            if clarification_data:
                update_data['clarification_data'] = clarification_data

            if existing:
                # Update existing conversation with new messages
                await self.conversation_store.update_conversation(session_id, update_data)
            else:
                # Create new conversation record
                conversation_data = {
                    'user_type': session_state.get('user_type', 'unknown'),
                    'user_type_confidence': session_state.get('user_type_confidence', 0.0),
                    'conversation_history': session_state['conversation_history'],
                    'metadata': session_state.get('metadata', {}),
                    'preferences': session_state.get('preferences', {})
                }
                if clarification_data:
                    conversation_data['clarification_data'] = clarification_data

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
    
    async def start_clarification_flow(
        self,
        query: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Start a new clarification question flow
        
        Args:
            query: User's original query
            session_id: Session identifier
            
        Returns:
            Formatted response with first question or error
        """
        session_state = await self.session_manager.get_or_create_session(session_id)
        
        # Generate clarifying questions
        clarification_state = await self.clarification_handler.generate_questions(query)
        
        if not clarification_state:
            # No questions generated or error occurred
            return self.clarification_handler.format_error(
                "Could not generate clarifying questions"
            )
        
        # Store clarification state in session
        session_state['clarification_state'] = clarification_state.to_dict()
        session_state['metadata']['clarification_count'] = session_state['metadata'].get('clarification_count', 0) + 1
        session_state['metadata']['clarification_started_at'] = datetime.now().isoformat()
        session_state['metadata']['original_clarification_query'] = query

        # Add to conversation history
        self._add_to_history(
            session_state,
            role='user',
            content=query,
            metadata={
                'type': 'clarification_trigger',
                'total_questions': len(clarification_state.questions)
            }
        )

        await self._update_and_save_session(session_id, session_state)
        
        # Return first question
        return self.clarification_handler.format_question_for_ui(clarification_state)
    
    async def handle_clarification_answer(
        self,
        answer: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Handle user's answer to a clarification question
        
        Args:
            answer: User's answer text
            session_id: Session identifier
            
        Returns:
            Formatted response with next question or completion
        """
        session_state = await self.session_manager.get_or_create_session(session_id)
        
        # Get clarification state from session
        state_dict = session_state.get('clarification_state')
        if not state_dict:
            return self._create_error_response("No active clarification flow found")
        
        # Restore state
        clarification_state = ClarificationState.from_dict(state_dict)
        
        # Get current question and record answer
        current_question = clarification_state.get_current_question()
        if not current_question:
            return self._create_error_response("No current question found")
        
        clarification_state.add_answer(current_question['id'], answer)
        
        # Update session with new state
        session_state['clarification_state'] = clarification_state.to_dict()
        
        # Add to collected entities for backend use (use string keys for Firestore)
        if 'clarification_answers' not in session_state['collected_entities']:
            session_state['collected_entities']['clarification_answers'] = {}

        question_id_str = str(current_question['id'])
        session_state['collected_entities']['clarification_answers'][question_id_str] = {
            'question': current_question['question'],
            'category': current_question['category'],
            'answer': answer
        }

        # Add Q&A to conversation history
        qa_metadata = {
            'type': 'clarification_question',
            'question_id': current_question['id'],
            'category': current_question['category']
        }
        self._add_to_history(session_state, 'assistant', current_question['question'], qa_metadata)

        answer_metadata = {
            'type': 'clarification_answer',
            'question_id': current_question['id'],
            'category': current_question['category']
        }
        self._add_to_history(session_state, 'user', answer, answer_metadata)

        await self._update_and_save_session(session_id, session_state)
        
        # Check if complete or return next question
        if clarification_state.is_complete():
            # Clear clarification state and mark as complete
            session_state['clarification_state'] = None
            session_state['clarification_complete'] = True
            session_state['metadata']['clarification_completed_at'] = datetime.now().isoformat()
            session_state['metadata']['total_clarification_answers'] = len(clarification_state.answers)

            await self._update_and_save_session(session_id, session_state)

            # Automatically call intent classifier now that clarification is complete
            intent_result = await self.call_intent_classifier(session_id)
            
            response = self.clarification_handler.format_question_for_ui(clarification_state)
            response['summary'] = clarification_state.get_summary()
            
            # Add intent classification result to response if successful
            if intent_result and 'error' not in intent_result:
                response['intent_classification'] = intent_result
            
            return response
        else:
            # Return next question
            return self.clarification_handler.format_question_for_ui(clarification_state)
    
    async def get_clarification_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get summary of clarification answers
        
        Args:
            session_id: Session identifier
            
        Returns:
            Summary dictionary or None if no clarification data
        """
        session_state = await self.session_manager.get_or_create_session(session_id)
        
        state_dict = session_state.get('clarification_state')
        if not state_dict:
            # Check if there's completed clarification data in collected_entities
            return session_state.get('collected_entities', {}).get('clarification_answers')
        
        clarification_state = ClarificationState.from_dict(state_dict)
        return clarification_state.get_summary()
    
    def is_clarification_active(self, session_state: Dict[str, Any]) -> bool:
        """
        Check if there's an active clarification flow
        
        Args:
            session_state: Current session state
            
        Returns:
            True if clarification is in progress
        """
        state_dict = session_state.get('clarification_state')
        if not state_dict:
            return False
        
        clarification_state = ClarificationState.from_dict(state_dict)
        return not clarification_state.is_complete()
    
    async def call_intent_classifier(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Call the intent classifier agent with session data
        
        Args:
            session_id: Session identifier to retrieve clarification data
            
        Returns:
            Intent classification result or None if error
        """
        try:
            # Call backend API endpoint with session_id
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{settings.backend_url}/intent-classifier",
                    params={"session_id": session_id}
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            import logging
            logging.error(f"Error calling intent classifier: {e}")
            return None
    
    def should_trigger_clarification(self, message: str, session_state: Dict[str, Any]) -> bool:
        """
        Determine if a query should trigger clarification questions
        
        Args:
            message: User message
            session_state: Current session state
            
        Returns:
            True if clarification should be triggered
        """
        # Don't trigger if clarification was already completed or is active
        if session_state.get('clarification_complete'):
            return False
        
        if self.is_clarification_active(session_state):
            return False
        
        # Check if this is the first real query (after welcome message)
        history = session_state.get('conversation_history', [])
        user_messages = [h for h in history if h.get('role') == 'user']
        
        # Trigger clarification on first substantive query
        # Skip very short messages or greetings
        if len(user_messages) == 0 and len(message.strip()) > 10:
            # Check if it looks like a destination request
            destination_keywords = ['find', 'suggest', 'recommend', 'looking for', 'want to', 'travel', 'visit', 'trip', 'europe', 'city', 'place']
            message_lower = message.lower()
            return any(keyword in message_lower for keyword in destination_keywords)
        
        return False


# Singleton instance
orchestrator = ConversationOrchestrator()
