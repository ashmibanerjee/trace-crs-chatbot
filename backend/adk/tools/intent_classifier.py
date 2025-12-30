from typing import Optional
from google.genai import types
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse, LlmRequest

from utils.firestore_utils import get_firestore_client


def _format_clarification_as_text(clarification_data: dict) -> str:
    """
    Format clarification data as readable text for injection into LLM request.
    
    Args:
        clarification_data: Dict with 'query' and 'clarifying_questions'
        
    Returns:
        Formatted string representation
    """
    query = clarification_data.get('query', '')
    questions = clarification_data.get('clarifying_questions', [])

    formatted = f"User's Original Query: {query}\n\n"
    formatted += "Clarifying Questions and Answers:\n"

    for q in questions:
        formatted += f"\nQ{q['id']} [{q['category']}]: {q['question']}\n"
        formatted += f"Answer: {q.get('answer', 'No answer provided')}\n"

    return formatted


def check_clarification_status_callback(
        callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmResponse]:
    """
    Callback to check Firestore and inject clarification data into the LLM request.
    Blocks execution if 'clarification_complete' is False or missing.
    If complete, injects the query + Q&A data into the request.
    """
    print(f"[Callback] Invoked for agent: {callback_context.agent_name}")

    # Extract session_id
    session_id = callback_context.session.id

    if not session_id:
        print("[Callback] WARNING: Could not extract session_id.")
        return None

    print(f"[Callback] Checking Firestore for session: {session_id}")

    try:
        # 1. Get Firestore client with credentials from .env
        db = get_firestore_client()

        # 2. Synchronously retrieve the conversation document
        doc_ref = db.collection('conversations').document(session_id)
        doc_snapshot = doc_ref.get()

        if not doc_snapshot.exists:
            print(f"[Callback] Conversation {session_id} not found in Firestore. Blocking.")
            return LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[types.Part(text="Error: Conversation not found. Please complete clarification first.")]
                )
            )

        # Convert to dict
        doc = doc_snapshot.to_dict()

        # 3. Check the flag (nested in clarification_data)
        clarification_data_raw = doc.get('clarification_data', {})
        clarification_complete = clarification_data_raw.get('clarification_complete', False)

        # 4. Decision Logic
        if not clarification_complete:
            print("[Callback] Clarification INCOMPLETE. Skipping Model execution.")
            return LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[types.Part(text="Please complete all clarification questions before intent classification.")]
                )
            )

        # 5. Clarification is complete - extract and inject data
        print("[Callback] Clarification complete. Injecting clarification data into request.")
        if not clarification_data_raw:
            print("[Callback] WARNING: Clarification marked complete but no data found.")
            return None  # Proceed without injection

        # 6. Format clarification data as text
        clarification_text = _format_clarification_as_text(clarification_data_raw)

        # 7. Inject into the LLM request
        if llm_request.contents and len(llm_request.contents) > 0:
            # Find the last user message
            for content in reversed(llm_request.contents):
                if content.role == 'user':
                    # Prepend clarification data to the existing user message
                    clarification_part = types.Part(text=clarification_text)

                    # Insert at the beginning of the parts list
                    if content.parts:
                        content.parts.insert(0, clarification_part)
                    else:
                        content.parts = [clarification_part]

                    print(f"[Callback] Injected clarification data into user message.")
                    break

        print("[Callback] Proceeding to Model with injected clarification data.")
        return None  # Proceed with modified LLM call

    except Exception as e:
        print(f"[Callback] Error checking clarification status: {e}")
        import traceback
        traceback.print_exc()
        # Fail safe: Block execution if DB fails
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part(text=f"Error checking clarification status: {str(e)}")]
            )
        )
