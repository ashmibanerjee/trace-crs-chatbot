"""
Clarification Question Handler
Manages the generation and collection of clarifying questions
"""
from typing import Dict, Any, List, Optional
import json
import httpx
from config import settings


class ClarificationState:
    """Tracks the state of clarifying questions for a session"""
    
    def __init__(self, questions: List[Dict[str, Any]], original_query: str):
        """
        Initialize clarification state
        
        Args:
            questions: List of question dictionaries with id, category, question, answer
            original_query: The original user query that triggered questions
        """
        self.original_query = original_query
        self.questions = questions
        self.answers = {}
        self.current_index = 0
    
    def get_current_question(self) -> Optional[Dict[str, Any]]:
        """Get the current unanswered question"""
        if self.current_index < len(self.questions):
            return self.questions[self.current_index]
        return None
    
    def add_answer(self, question_id: int, answer: str) -> bool:
        """
        Record an answer to a question
        
        Args:
            question_id: The ID of the question being answered
            answer: The user's response
            
        Returns:
            True if answer was recorded successfully
        """
        # Get current question to ensure we're answering the right one
        current_question = self.get_current_question()
        if not current_question or current_question['id'] != question_id:
            return False
        
        # Record the answer - use string key for Firestore compatibility
        question_id_str = str(question_id)
        current_question['answer'] = answer
        self.answers[question_id_str] = {
            'question': current_question['question'],
            'category': current_question['category'],
            'answer': answer
        }
        
        # Move to next question
        self.current_index += 1
        return True
    
    def is_complete(self) -> bool:
        """Check if all questions have been answered"""
        return self.current_index >= len(self.questions)
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current progress information"""
        return {
            'answered': len(self.answers),
            'total': len(self.questions),
            'current_index': self.current_index,
            'percentage': int((len(self.answers) / len(self.questions)) * 100) if self.questions else 100
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all questions and answers"""
        return {
            'original_query': self.original_query,
            'total_questions': len(self.questions),
            'answers': self.answers,
            'complete': self.is_complete()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize state to dictionary for session storage"""
        # Ensure all keys are strings for Firestore compatibility
        return {
            'original_query': self.original_query,
            'questions': self.questions,
            'answers': {str(k): v for k, v in self.answers.items()},
            'current_index': self.current_index
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ClarificationState':
        """Restore state from dictionary"""
        state = cls(
            questions=data.get('questions', []),
            original_query=data.get('original_query', '')
        )
        state.answers = data.get('answers', {})
        state.current_index = data.get('current_index', 0)
        return state


def _generate_fallback_questions(query: str) -> ClarificationState:
    """
    Generate fallback clarifying questions when API is unavailable

    Args:
        query: User's original query

    Returns:
        ClarificationState with basic questions
    """
    fallback_questions = [
        {
            'id': 1,
            'category': 'preference_temporal',
            'question': 'When are you planning to travel? (e.g., specific dates, season, or flexible)',
            'answer': None
        },
        {
            'id': 2,
            'category': 'preference_personal',
            'question': 'What is your approximate budget for this trip? (e.g., budget-friendly, mid-range, luxury)',
            'answer': None
        },
        {
            'id': 3,
            'category': 'preference_purpose',
            'question': 'What are you most interested in? (e.g., culture, nature, adventure, relaxation, nightlife)',
            'answer': None
        },
        {
            'id': 4,
            'category': 'preference_spatial',
            'question': 'Do you prefer cities, coastal areas, countryside, or mountains?',
            'answer': None
        },
        {
            'id': 5,
            'category': 'comparison_sustainability',
            'question': 'How important is sustainability in your travel choices? (e.g., very important, somewhat important, not a priority)',
            'answer': None
        }
    ]

    return ClarificationState(
        questions=fallback_questions,
        original_query=query
    )


class ClarificationHandler:
    """
    Handles the flow of clarifying questions
    Integrates with the ADK clarifying question agent
    """
    
    async def generate_questions(self, query: str) -> Optional[ClarificationState]:
        """
        Generate clarifying questions for a user query by calling backend API

        Args:
            query: User's original query

        Returns:
            ClarificationState object or None if generation fails
        """
        try:
            # Call backend API endpoint
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{settings.backend_api_url}/generate-clarifying-questions",
                    params={"user_input": query}
                )
                response.raise_for_status()
                result = response.json()

            # Transform API response to expected format
            if result and result.get('clarifying_questions'):
                questions = result['clarifying_questions']
                return ClarificationState(
                    questions=questions,
                    original_query=result.get('query', query)
                )

            # Fallback: Generate mock questions if API returns empty
            print(f"Warning: API returned no questions, using fallback for: {query}")
            return _generate_fallback_questions(query)

        except httpx.HTTPError as e:
            print(f"HTTP error calling backend API: {e}")
            return _generate_fallback_questions(query)
        except Exception as e:
            print(f"Error generating clarifying questions: {e}")
            return _generate_fallback_questions(query)

    def format_question_for_ui(
        self,
        state: ClarificationState
    ) -> Dict[str, Any]:
        """
        Format current question for display in UI
        
        Args:
            state: Current clarification state
            
        Returns:
            Formatted response for frontend
        """
        current_question = state.get_current_question()
        progress = state.get_progress()
        
        if not current_question:
            return self._format_completion(state)
        
        # Format the question text with progress
        question_text = (
            # f"**Question {progress['current_index'] + 1} of {progress['total']}** "
            # f"({progress['percentage']}% complete)\n\n"
            # f"**Category:** {current_question['category'].replace('_', ' ').title()}\n\n"
            f"{current_question['question']}"
        )
        
        return {
            'type': 'clarification_question',
            'text': question_text,
            'question_id': current_question['id'],
            'progress': progress,
            'metadata': {
                'category': current_question['category'],
                'clarification_active': True
            }
        }
    
    def _format_completion(self, state: ClarificationState) -> Dict[str, Any]:
        """Format completion message when all questions are answered"""
        summary = state.get_summary()
        
        completion_text = (
            "✅ **All questions answered!**\n\n"
            "Thank you for providing that information. "
            "Let me now find the best recommendations for you based on your preferences."
        )
        
        return {
            'type': 'clarification_complete',
            'text': completion_text,
            'summary': summary,
            'metadata': {
                'clarification_active': False,
                'clarification_complete': True
            }
        }
    
    def format_error(self, error_message: str) -> Dict[str, Any]:
        """Format error response"""
        return {
            'type': 'clarification_error',
            'text': f"⚠️ Unable to generate clarifying questions: {error_message}\n\nProceeding with your original query.",
            'metadata': {
                'clarification_active': False,
                'error': True
            }
        }
