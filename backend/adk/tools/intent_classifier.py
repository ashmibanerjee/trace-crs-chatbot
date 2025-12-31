from typing import Optional
from google.genai import types
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse, LlmRequest

from backend.adk.tools.utils import inject_to_llm_request, format_clarification_as_text, get_firestore_document


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
        # 1. Retrieve conversation document from Firestore
        doc, error_response = get_firestore_document(
            collection_name='conversations',
            session_id=session_id,
            error_message="Error: Conversation not found. Please complete clarification first.",
            log_prefix="[Callback]"
        )

        if error_response:
            return error_response

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
        clarification_text = format_clarification_as_text(clarification_data_raw)

        inject_to_llm_request(clarification_text, llm_request) # in-place modification happens

        print("[Callback] Proceeding to Model with injected clarification data.")
        return None  # Proceed with modified LLM call

    except Exception as e:
        # Note: Firestore errors are already handled by get_firestore_document()
        # This catches any other unexpected errors in the callback logic
        print(f"[Callback] Error in callback logic: {e}")
        import traceback
        traceback.print_exc()
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part(text=f"Error checking clarification status: {str(e)}")]
            )
        )


