"""
Frontend Helper Functions
Reusable utilities for the Chainlit app
"""
import chainlit as cl
from typing import Dict, Any, Optional
import uuid
from datetime import datetime
from database.config import get_conversation_store


async def get_or_create_session_id() -> str:
    """Get existing session ID or create a new one"""
    session_id = cl.user_session.get("id")
    if not session_id:
        session_id = str(uuid.uuid4())
        cl.user_session.set("id", session_id)
    return session_id


async def reset_session_state():
    """Reset all session state flags"""
    cl.user_session.set("clarification_active", False)
    cl.user_session.set("clarification_complete", False)
    cl.user_session.set("feedback_rating", None)
    cl.user_session.set("feedback_text_collected", False)
    cl.user_session.set("original_query", None)


async def create_new_session():
    """Create a new session ID and reset session state"""
    new_session_id = str(uuid.uuid4())
    cl.user_session.set("id", new_session_id)
    await reset_session_state()
    print(f"New session created: {new_session_id}")


async def save_feedback(session_id: str, rating: int, feedback_text: Optional[str] = None):
    """
    Save user feedback to conversations collection

    Args:
        session_id: Session identifier
        rating: Star rating (1-5)
        feedback_text: Optional text feedback
    """
    try:
        conversation_store = get_conversation_store()

        feedback_data = {
            'feedback': {
                'rating': rating,
                'feedback_text': feedback_text,
                'timestamp': datetime.now().isoformat(),
                'feedback_type': 'recommendation_rating'
            }
        }

        success = await conversation_store.update_conversation(session_id, feedback_data)

        if success:
            print(f"Feedback saved for session {session_id}: {rating} stars")
        else:
            print(f"Warning: Could not save feedback for session {session_id}")

    except Exception as e:
        print(f"Error saving feedback: {e}")
        import traceback
        traceback.print_exc()


def create_action(name: str, payload: Dict[str, Any], label: str,
                  description: str = "", bg_color: str = "#6366f1") -> cl.Action:
    """
    Create a standardized action button

    Args:
        name: Action name
        payload: Action payload
        label: Button label
        description: Button description
        bg_color: Background color hex code

    Returns:
        Chainlit Action object
    """
    return cl.Action(
        name=name,
        payload=payload,
        label=label,
        description=description,
        style={
            "background-color": bg_color,
            "color": "white",
            "border-radius": "8px",
            "padding": "12px 24px",
            "font-weight": "500"
        }
    )


def create_sample_query_actions():
    """Create sample query action buttons"""
    queries = [
        {
            "name": "sample_query_1",
            "query": "Find a low-budget, walkable city in Europe with unusual museums or a hidden, alternative "
                     "nightlife scene.",
            "label": "🎨 Find a low-budget, walkable city in Europe with unusual museums or a hidden, alternative "
                     "nightlife scene.",
            "color": "#6366f1"
        },
        {
            "name": "sample_query_2",
            "query": "Quiet European coastal city with good air quality, affordable, not touristy, with interesting nightlife options.",
            "label": "🌊 Quiet European coastal city with good air quality, affordable, not touristy, with interesting nightlife options.",
            "color": "#10b981"
        },
        {
            "name": "sample_query_3",
            "query": "Best European cities for unique, artistic experiences and independent cinema, avoiding "
                     "mainstream tourist attractions?",
            "label": "🎬 Best European cities for unique, artistic experiences and independent cinema, avoiding "
                     "mainstream tourist attractions?",
            "color": "#f59e0b"
        }
    ]

    return [
        create_action(
            name=q["name"],
            payload={"query": q["query"]},
            label=q["label"],
            description="",
            bg_color=q["color"]
        )
        for q in queries
    ]


def create_rating_actions():
    """Create star rating action buttons"""
    return [
        cl.Action(
            name=f"rating_{i}",
            value=str(i),
            payload={"rating": i, "type": "rating"},
            label=f"{'⭐' * i} ({i}/5)",
            description=f"{i} star{'s' if i != 1 else ''}"
        )
        for i in range(1, 6)
    ]
