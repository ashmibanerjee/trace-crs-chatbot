from typing import Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.genai import types

from backend.adk.tools.utils import get_firestore_document, inject_to_llm_request
import json


def _format_context_as_text(intent_data: dict, ca_rec_data: dict, rec_base_data: dict) -> str:
    """Format intent classification, context-aware and baseline recommendations data as text for LLM to include in
    context field."""

    context_obj = {
        "intent_classification": intent_data if intent_data else None,
        "baseline_recommendation": {
            "recommendation": ca_rec_data.get('recommendation') if ca_rec_data else None,
            "explanation": ca_rec_data.get('explanation') if ca_rec_data else None,
            "trade_off": ca_rec_data.get('trade_off') if ca_rec_data else None
        } if ca_rec_data else None,
        "context_aware_recommendation": {
            "recommendation": rec_base_data.get('recommendation') if rec_base_data else None,
            "explanation": rec_base_data.get('explanation') if rec_base_data else None,
            "trade_off": rec_base_data.get('trade_off') if rec_base_data else None
        } if rec_base_data else None
    }
    return f"""
=== CONTEXT DATA (Include this in your 'context' field) ===
{json.dumps(context_obj, indent=2)}
=== END CONTEXT DATA ===
"""


def cfe_callback(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:
    print(f"[CFE Callback] Invoked for agent: {callback_context.agent_name}")

    session_id = callback_context.session.id

    if not session_id:
        print("[CFE Callback] WARNING: Could not extract session_id.")
        return None

    print(f"[CFE Callback] Checking Firestore for session: {session_id}")
    error = None
    try:
        intent_data, error_response_0 = get_firestore_document(
            collection_name='intent_classifier_responses',
            session_id=session_id,
            error_message="Error: Intent classification data not found. Please run intent classifier first.",
            log_prefix="[CFE Callback]"
        )

        ca_rec_data, error_response_1 = get_firestore_document(
            collection_name='context_aware_recommendations',
            session_id=session_id,
            error_message="Error: Content aware recommendations data not found. Please run CA recommendations first.",
            log_prefix="[CFE Callback]"
        )
        rec_base_data, error_response_2 = get_firestore_document(
            collection_name='baseline_recommendations',
            session_id=session_id,
            error_message="Error: Content aware recommendations data not found. Please run CA recommendations first.",
            log_prefix="[CFE Callback]")

        if error := (error_response_0 or error_response_1 or error_response_2):
            return error

        if not intent_data or not ca_rec_data or not rec_base_data:
            print(f"[CFE Callback] Empty data for session {session_id}.")
            return None

        # 4. Format context as text
        context_text = _format_context_as_text(intent_data, ca_rec_data, rec_base_data)

        # 5. Inject into LLM request
        inject_to_llm_request(context_text, llm_request)

        print("[CFE Callback] Successfully injected context into LLM request.")
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
