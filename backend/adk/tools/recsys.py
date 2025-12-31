from typing import Optional
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse, LlmRequest
from google.genai import types

from .utils import inject_to_llm_request, format_intent_context_as_text, get_firestore_document


def recsys_callback(callback_context: CallbackContext, llm_request: LlmRequest, has_context: bool) -> Optional[LlmResponse]:
    """
    Callback to retrieve intent classifier response from Firestore and inject into LLM request.

    Args:
        callback_context: Agent callback context
        llm_request: The LLM request to modify
        has_context: Whether to use context from Firestore

    Returns:
        LlmResponse if blocking execution, None to proceed with modified request
    """
    print(f"[Recsys Callback] Invoked for agent: {callback_context.agent_name}")

    if not has_context:
        print("[Recsys Callback] has_context=False, proceeding without context injection.")
        return None

    session_id = callback_context.session.id

    if not session_id:
        print("[Recsys Callback] WARNING: Could not extract session_id.")
        return None

    print(f"[Recsys Callback] Checking Firestore for session: {session_id}")

    try:
        # 1. Retrieve intent classifier response document from Firestore
        intent_data, error_response = get_firestore_document(
            collection_name='intent_classifier_responses',
            session_id=session_id,
            error_message="Error: Intent classification data not found. Please run intent classifier first.",
            log_prefix="[Recsys Callback]"
        )

        if error_response:
            return error_response

        if not intent_data:
            print(f"[Recsys Callback] Empty intent data for session {session_id}.")
            return None

        # 4. Format context as text
        context_text = format_intent_context_as_text(intent_data)

        # 5. Inject into LLM request
        inject_to_llm_request(context_text, llm_request)

        print("[Recsys Callback] Successfully injected intent context into LLM request.")
        return None  # Proceed with modified request

    except Exception as e:
        # Note: Firestore errors are already handled by get_firestore_document()
        # This catches any other unexpected errors in the callback logic
        print(f"[Recsys Callback] Error in callback logic: {e}")
        import traceback
        traceback.print_exc()

        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part(text=f"Error retrieving intent context: {str(e)}")]
            )
        )

