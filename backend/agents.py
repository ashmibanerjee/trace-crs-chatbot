"""
Backend Agent Interface
This is a minimal working backend that can be replaced with complex ADK agents later.
"""
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from datetime import datetime
import asyncio


class AgentResponse:
    """Standard response format from agents"""
    
    def __init__(
        self,
        text: str,
        agent_name: str,
        action: str,
        metadata: Optional[Dict[str, Any]] = None,
        recommendations: Optional[List[Dict]] = None,
        requires_clarification: bool = False,
        clarification_options: Optional[List[str]] = None
    ):
        self.text = text
        self.agent_name = agent_name
        self.action = action
        self.metadata = metadata or {}
        self.recommendations = recommendations or []
        self.requires_clarification = requires_clarification
        self.clarification_options = clarification_options or []
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'text': self.text,
            'agent_name': self.agent_name,
            'action': self.action,
            'metadata': self.metadata,
            'recommendations': self.recommendations,
            'requires_clarification': self.requires_clarification,
            'clarification_options': self.clarification_options,
            'timestamp': self.timestamp
        }


class BaseAgent(ABC):
    """Abstract base class for all agents"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    @abstractmethod
    async def process(self, message: str, context: Dict[str, Any]) -> AgentResponse:
        """Process a message and return a response"""
        pass


class ClarificationAgent(BaseAgent):
    """Agent that asks clarifying questions"""
    
    def __init__(self):
        super().__init__(
            name="clarification",
            description="Gathers missing information from users"
        )
        
        self.required_fields = ['destination', 'dates', 'budget', 'interests']
    
    async def process(self, message: str, context: Dict[str, Any]) -> AgentResponse:
        """Check for missing information and ask clarifying questions"""
        
        collected = context.get('collected_entities', {})
        missing = [field for field in self.required_fields if field not in collected]
        
        if missing:
            field = missing[0]
            question_map = {
                'destination': "Where would you like to travel?",
                'dates': "When are you planning to travel?",
                'budget': "What's your approximate budget for this trip?",
                'interests': "What are your main interests? (e.g., nature, culture, adventure)"
            }
            
            return AgentResponse(
                text=question_map[field],
                agent_name=self.name,
                action="CLARIFY",
                requires_clarification=True,
                clarification_options=[
                    "I'm flexible",
                    "Let me specify"
                ] if field != 'destination' else []
            )
        
        return AgentResponse(
            text="I have all the information I need!",
            agent_name=self.name,
            action="COMPLETE"
        )


class IntentAgent(BaseAgent):
    """Agent that classifies user intent"""
    
    def __init__(self):
        super().__init__(
            name="intent",
            description="Classifies user intent from messages"
        )
        
        self.intent_keywords = {
            'FIND_DESTINATION': ['recommend', 'suggest', 'find', 'looking for', 'where should'],
            'GET_INFO': ['tell me about', 'information', 'what is', 'how is'],
            'SUSTAINABILITY_QUERY': ['eco', 'sustainable', 'green', 'carbon', 'environmental'],
            'BOOK': ['book', 'reserve', 'booking'],
            'PREFERENCE_UPDATE': ['i prefer', 'change', 'actually', 'instead']
        }
    
    async def process(self, message: str, context: Dict[str, Any]) -> AgentResponse:
        """Classify the intent of the message"""
        
        message_lower = message.lower()
        detected_intent = 'CHITCHAT'
        confidence = 0.5
        
        for intent, keywords in self.intent_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                detected_intent = intent
                confidence = 0.85
                break
        
        return AgentResponse(
            text=f"I understand you want to: {detected_intent}",
            agent_name=self.name,
            action="CLASSIFY",
            metadata={
                'intent': detected_intent,
                'confidence': confidence
            }
        )


class RecommendationAgent(BaseAgent):
    """Agent that provides recommendations"""
    
    def __init__(self):
        super().__init__(
            name="recommendation",
            description="Provides sustainable tourism recommendations"
        )
        
        # Mock data - replace with real database/API later
        self.mock_destinations = [
            {
                'id': 'dest_1',
                'name': 'Costa Rica Eco-Lodge',
                'description': 'Sustainable rainforest lodge with solar power and organic farm',
                'sustainability_score': 9.2,
                'carbon_offset': '100%',
                'certifications': ['Green Globe', 'Rainforest Alliance'],
                'image_url': 'https://example.com/costa-rica.jpg'
            },
            {
                'id': 'dest_2',
                'name': 'Iceland Geothermal Resort',
                'description': 'Carbon-neutral resort powered entirely by geothermal energy',
                'sustainability_score': 9.5,
                'carbon_offset': '120%',
                'certifications': ['EarthCheck', 'Green Key'],
                'image_url': 'https://example.com/iceland.jpg'
            },
            {
                'id': 'dest_3',
                'name': 'Bali Permaculture Village',
                'description': 'Community-based eco-tourism with traditional farming practices',
                'sustainability_score': 8.8,
                'carbon_offset': '95%',
                'certifications': ['Green Globe'],
                'image_url': 'https://example.com/bali.jpg'
            }
        ]
    
    async def process(self, message: str, context: Dict[str, Any]) -> AgentResponse:
        """Generate recommendations based on user preferences"""
        
        preferences = context.get('preferences', {})
        sustainability_weight = preferences.get('sustainability_weight', 0.8)
        
        # Simple filtering based on sustainability focus
        recommendations = sorted(
            self.mock_destinations,
            key=lambda x: x['sustainability_score'],
            reverse=True
        )[:2]  # Return top 2
        
        response_text = (
            f"🌿 Here are my top sustainable recommendations for you:\n\n"
        )
        
        for i, rec in enumerate(recommendations, 1):
            response_text += (
                f"{i}. **{rec['name']}** (Sustainability Score: {rec['sustainability_score']}/10)\n"
                f"   {rec['description']}\n"
                f"   🌱 Carbon Offset: {rec['carbon_offset']}\n\n"
            )
        
        return AgentResponse(
            text=response_text,
            agent_name=self.name,
            action="RECOMMEND",
            recommendations=recommendations,
            metadata={
                'total_results': len(recommendations),
                'sustainability_weight': sustainability_weight
            }
        )


class CoordinatorAgent(BaseAgent):
    """Main coordinator that routes to specialized agents"""
    
    def __init__(self):
        super().__init__(
            name="coordinator",
            description="Routes user queries to appropriate agents"
        )
        
        # Initialize specialized agents
        self.clarification_agent = ClarificationAgent()
        self.intent_agent = IntentAgent()
        self.recommendation_agent = RecommendationAgent()
    
    async def process(self, message: str, context: Dict[str, Any]) -> AgentResponse:
        """Main routing logic"""
        
        # Step 1: Check if clarification is needed
        clarification_response = await self.clarification_agent.process(message, context)
        if clarification_response.requires_clarification:
            return clarification_response
        
        # Step 2: Classify intent
        intent_response = await self.intent_agent.process(message, context)
        intent = intent_response.metadata.get('intent', 'CHITCHAT')
        
        # Step 3: Route based on intent
        if intent == 'FIND_DESTINATION':
            return await self.recommendation_agent.process(message, context)
        
        elif intent == 'SUSTAINABILITY_QUERY':
            return AgentResponse(
                text=(
                    "🌍 I specialize in sustainable tourism! All my recommendations prioritize:\n"
                    "• Low carbon footprint\n"
                    "• Eco-certifications (Green Globe, EarthCheck, etc.)\n"
                    "• Community-based tourism\n"
                    "• Renewable energy use\n\n"
                    "Would you like to see some eco-friendly destinations?"
                ),
                agent_name=self.name,
                action="INFORM"
            )
        
        elif intent == 'GET_INFO':
            return AgentResponse(
                text="I can provide information about sustainable destinations. Which place interests you?",
                agent_name=self.name,
                action="CLARIFY"
            )
        
        else:
            return AgentResponse(
                text=(
                    "👋 I'm your sustainable tourism assistant! I can help you:\n"
                    "• Find eco-friendly destinations\n"
                    "• Learn about sustainability features\n"
                    "• Compare carbon footprints\n\n"
                    "What would you like to explore?"
                ),
                agent_name=self.name,
                action="GREET"
            )


class MinimalBackend:
    """
    Minimal backend that can be replaced with complex ADK agents.
    Provides the same interface for easy swapping.
    """
    
    def __init__(self):
        self.coordinator = CoordinatorAgent()
        self.user_type_patterns = {
            'explorative': ['explore', 'discover', 'show me', 'what about', 'flexible', 'open to'],
            'goal_oriented': ['book', 'need', 'specific', 'must have', 'requirements', 'quickly'],
            'sustainability_focused': ['eco', 'sustainable', 'green', 'carbon', 'environmental', 'organic']
        }
    
    async def process_message(
        self,
        message: str,
        session_state: Dict[str, Any]
    ) -> AgentResponse:
        """
        Main entry point for processing messages.
        This signature should match the ADK backend interface.
        """
        
        # Extract context from session state
        context = {
            'user_type': session_state.get('user_type'),
            'preferences': session_state.get('preferences', {}),
            'collected_entities': session_state.get('collected_entities', {}),
            'conversation_history': session_state.get('conversation_history', [])
        }
        
        # Process through coordinator
        response = await self.coordinator.process(message, context)
        
        # Update session state based on response
        self._update_session_state(session_state, message, response)
        
        return response
    
    def _update_session_state(
        self,
        session_state: Dict[str, Any],
        message: str,
        response: AgentResponse
    ):
        """Update session state with new information"""
        
        # Add to conversation history in training-ready format
        if 'conversation_history' not in session_state:
            session_state['conversation_history'] = []
        
        # User message
        session_state['conversation_history'].append({
            'role': 'user',
            'content': message,
            'timestamp': datetime.now().isoformat(),
            'metadata': {
                'message_length': len(message),
                'entities_mentioned': list(session_state.get('collected_entities', {}).keys())
            }
        })
        
        # Assistant response
        session_state['conversation_history'].append({
            'role': 'assistant',
            'content': response.text,
            'timestamp': response.timestamp,
            'metadata': {
                'agent_name': response.agent_name,
                'action': response.action,
                'intent': response.metadata.get('intent'),
                'recommendations_provided': len(response.recommendations),
                'clarification_required': response.requires_clarification
            }
        })
        
        # Infer user type from conversation patterns
        self._infer_user_type(session_state, message)
        
        # Update conversation metadata
        if 'metadata' not in session_state:
            session_state['metadata'] = {}
        session_state['metadata']['total_turns'] = session_state['metadata'].get('total_turns', 0) + 1
        if response.metadata.get('intent'):
            session_state['metadata'].setdefault('intents', []).append(response.metadata['intent'])
        if response.requires_clarification:
            session_state['metadata']['clarification_count'] = session_state['metadata'].get('clarification_count', 0) + 1
        
        # Extract entities from message (simple keyword matching)
        if 'collected_entities' not in session_state:
            session_state['collected_entities'] = {}
        
        # Simple entity extraction
        message_lower = message.lower()
        if any(word in message_lower for word in ['costa rica', 'bali', 'iceland', 'japan']):
            session_state['collected_entities']['destination'] = True
        
        if any(word in message_lower for word in ['week', 'month', 'january', 'summer']):
            session_state['collected_entities']['dates'] = True
        
        if any(word in message_lower for word in ['$', 'budget', 'cheap', 'luxury']):
            session_state['collected_entities']['budget'] = True
        
        if any(word in message_lower for word in ['nature', 'culture', 'adventure', 'relaxation']):
            session_state['collected_entities']['interests'] = True
        
        # Initialize preferences if not present
        if 'preferences' not in session_state:
            session_state['preferences'] = {
                'sustainability_weight': 0.8
            }
    
    def _infer_user_type(
        self,
        session_state: Dict[str, Any],
        message: str
    ):
        """Infer user type from conversation patterns and message content"""
        
        message_lower = message.lower()
        scores = {'explorative': 0, 'goal_oriented': 0, 'sustainability_focused': 0}
        
        # Score based on keywords
        for user_type, keywords in self.user_type_patterns.items():
            score = sum(1 for keyword in keywords if keyword in message_lower)
            scores[user_type] += score
        
        # Score based on conversation behavior
        history_length = len(session_state.get('conversation_history', []))
        if history_length > 0:
            # Goal-oriented users ask direct questions early
            if history_length <= 4 and any(word in message_lower for word in ['book', 'specific', 'need']):
                scores['goal_oriented'] += 2
            
            # Explorative users ask multiple questions about different options
            metadata = session_state.get('metadata', {})
            if metadata.get('total_turns', 0) > 3:
                scores['explorative'] += 1
            
            # Sustainability-focused users mention eco terms repeatedly
            intents = metadata.get('intents', [])
            if intents.count('SUSTAINABILITY_QUERY') >= 2:
                scores['sustainability_focused'] += 3
        
        # Determine user type with highest score
        if sum(scores.values()) > 0:
            inferred_type = max(scores.items(), key=lambda x: x[1])[0]
            confidence = scores[inferred_type] / max(sum(scores.values()), 1)
            
            # Update session if confidence is reasonable
            if confidence > 0.3:
                session_state['user_type'] = inferred_type
                session_state['user_type_confidence'] = confidence
                
                # Adjust preferences based on user type
                if inferred_type == 'sustainability_focused':
                    session_state['preferences']['sustainability_weight'] = 1.0
                elif inferred_type == 'goal_oriented':
                    session_state['preferences']['sustainability_weight'] = 0.6
                else:  # explorative
                    session_state['preferences']['sustainability_weight'] = 0.8
