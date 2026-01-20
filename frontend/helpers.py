"""
Frontend Helper Functions
Reusable utilities for the Chainlit app
"""
import chainlit as cl
from typing import Dict, Any, Optional, List
import uuid
from datetime import datetime
from database.config import get_conversation_store
from pathlib import Path
import json
import random


async def get_or_create_session_id() -> str:
    """Get existing session ID or create a new one"""
    # Use "conversation_id" instead of "id" as "id" might be reserved by Chainlit
    session_id = cl.user_session.get("conversation_id")

    # If no session_id or if it's in old UUID format, create a new one
    if not session_id or "-" in session_id:
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        cl.user_session.set("conversation_id", session_id)
        print(f"[GET_OR_CREATE] Created/Reset conversation_id to: {session_id}")
    else:
        print(f"[GET_OR_CREATE] Using existing conversation_id: {session_id}")

    return session_id


async def reset_session_state():
    """Reset all session state flags"""
    cl.user_session.set("clarification_active", False)
    cl.user_session.set("clarification_complete", False)
    cl.user_session.set("feedback_rating", None)
    cl.user_session.set("feedback_text_collected", False)
    cl.user_session.set("feedback_in_progress", False)
    cl.user_session.set("current_feedback_question_index", 0)
    cl.user_session.set("waiting_for_feedback_text", False)
    cl.user_session.set("original_query", None)


async def create_new_session():
    """Create a new session ID and reset session state"""
    old_session_id = cl.user_session.get("conversation_id")
    new_session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    print(f"[SESSION_CHANGE] Old session: {old_session_id} → New session: {new_session_id}")

    # Reset state first, then set new session_id
    await reset_session_state()

    # Set the new session_id AFTER resetting state using "conversation_id" key
    cl.user_session.set("conversation_id", new_session_id)
    cl.user_session.set("welcome_shown", True)  # Don't show welcome again

    # Verify it was set
    verify_id = cl.user_session.get("conversation_id")
    print(f"[SESSION_VERIFY] conversation_id after setting: {verify_id}")

    if verify_id != new_session_id:
        print(f"[ERROR] conversation_id was not set correctly! Expected {new_session_id}, got {verify_id}")

    return new_session_id


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


async def save_feedback_answer(session_id: str, q_id: int, question: str, answer: Any, option_id: Optional[int] = None):
    """
    Save a single feedback answer to conversations collection iteratively

    Args:
        session_id: Session identifier
        q_id: Question ID
        question: Question text
        answer: Answer text
        option_id: Optional option ID if answer was from radio button
    """
    try:
        conversation_store = get_conversation_store()

        # Get existing conversation to preserve previous answers
        conversation = await conversation_store.get_conversation(session_id)

        # Initialize feedback_answers array if it doesn't exist
        if conversation and 'feedback_answers' in conversation:
            feedback_answers = conversation['feedback_answers']
        else:
            feedback_answers = []

        # Add new answer
        feedback_answer = {
            'q_id': q_id,
            'question': question,
            'answer': answer,
            'option_id': option_id,
            'timestamp': datetime.now().isoformat()
        }

        feedback_answers.append(feedback_answer)

        # Update conversation with new feedback answer
        success = await conversation_store.update_conversation(
            session_id,
            {'feedback_answers': feedback_answers}
        )

        if success:
            print(f"Feedback answer saved for session {session_id}, q_id: {q_id}")
        else:
            print(f"Warning: Could not save feedback answer for session {session_id}")

        return success

    except Exception as e:
        print(f"Error saving feedback answer: {e}")
        import traceback
        traceback.print_exc()
        return False


def load_feedback_questions() -> List[Dict[str, Any]]:
    """Load feedback questions from feedback_questions.json"""
    questions_path = Path(__file__).resolve().parent / "feedback_questions.json"

    if not questions_path.exists():
        print(f"Warning: feedback_questions.json not found at {questions_path}")
        return []

    try:
        data = json.loads(questions_path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError) as e:
        print(f"Error loading feedback_questions.json: {e}")
        return []


def create_action(
    name: str,
    payload: Dict[str, Any],
    label: str,
    description: str = "",
    bg_color: str = "#e0f2ff",
    text_color: str = "#0f172a",
    border_color: str = "#bae6fd",
    action_id: Optional[str] = None,
) -> cl.Action:
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
    action = cl.Action(
        name=name,
        payload=payload,
        label=label,
        description=description,
        style={
            "background-color": bg_color,
            "color": text_color,
            "border": f"1px solid {border_color}",
            "border-radius": "10px",
            "padding": "12px 16px",
            "font-weight": "500"
        }
    )

    if action_id:
        action.id = action_id

    return action


def _load_filtered_queries() -> List[str]:
    """Load query_text values from filtered_queries.json"""
    public_path = Path(__file__).resolve().parents[1] / "public" / "filtered_queries.json"
    if not public_path.exists():
        return []

    try:
        data = json.loads(public_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    if not isinstance(data, list):
        return []

    queries = [item.get("query_text") for item in data if isinstance(item, dict)]
    return [q for q in queries if isinstance(q, str) and q.strip()]


def create_sample_query_actions(seed: Optional[str] = None):
    """Create sample query action buttons"""
    all_queries = _load_filtered_queries()

    if len(all_queries) >= 3:
        rng = random.Random(seed) if seed is not None else random
        sampled = rng.sample(all_queries, 3)
    else:
        sampled = all_queries

    default_colors = ["#e0f2ff", "#e0f2ff", "#e0f2ff"]
    text_colors = ["#0f172a", "#0f172a", "#0f172a"]
    border_colors = ["#bae6fd", "#bae6fd", "#bae6fd"]
    emoji_prefixes = ["✨", "🌍", "🎒", "🗺️", "🌟", "🏙️"]
    actions = []

    for idx, query in enumerate(sampled, start=1):
        emoji = emoji_prefixes[(idx - 1) % len(emoji_prefixes)]
        label = f"{emoji} {query}"
        color_index = (idx - 1) % len(default_colors)
        actions.append(
            create_action(
                name=f"sample_query_{idx}",
                payload={"query": query},
                label=label,
                description="",
                bg_color=default_colors[color_index],
                text_color=text_colors[color_index],
                border_color=border_colors[color_index],
                action_id=f"sample_query_{idx}"
            )
        )

    return actions


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
