from typing import Optional, Tuple
from google.adk.models import LlmRequest, LlmResponse
from google.genai import types

from utils.firestore_utils import get_firestore_client


def get_firestore_document(
    collection_name: str,
    session_id: str,
    error_message: str,
    log_prefix: str = "[Callback]"
) -> Tuple[Optional[dict], Optional[LlmResponse]]:
    """
    Retrieve a document from Firestore by collection name and session ID.

    Args:
        collection_name: Name of the Firestore collection
        session_id: Document ID (session identifier)
        error_message: Error message to return if document not found
        log_prefix: Prefix for log messages (default: "[Callback]")

    Returns:
        Tuple of (document_data, error_response):
        - If successful: (document_dict, None)
        - If document not found or error: (None, LlmResponse with error)
    """
    try:
        # Get Firestore client
        db = get_firestore_client()

        # Retrieve document
        doc_ref = db.collection(collection_name).document(session_id)
        doc_snapshot = doc_ref.get()

        if not doc_snapshot.exists:
            print(f"{log_prefix} Document not found in {collection_name} for session {session_id}.")
            return None, LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[types.Part(text=error_message)]
                )
            )

        # Convert to dict
        doc_data = doc_snapshot.to_dict()
        return doc_data, None

    except Exception as e:
        print(f"{log_prefix} Error retrieving document from {collection_name}: {e}")
        import traceback
        traceback.print_exc()

        return None, LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part(text=f"Error retrieving data from {collection_name}: {str(e)}")]
            )
        )


def format_clarification_as_text(clarification_data: dict) -> str:
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


def format_intent_context_as_text(intent_data: dict) -> str:
    """
    Format intent classifier response data as readable text for injection into LLM request.

    Args:
        intent_data: Dict from intent_classifier_responses collection

    Returns:
        Formatted string representation with all context
    """
    formatted = "=== User Context and Intent ===\n\n"

    # 1. Input data (clarified Q&A and queries)
    input_data = intent_data.get('input', [])
    if input_data:
        formatted += "## Clarified User Queries:\n"
        for idx, context in enumerate(input_data, 1):
            query = context.get('user query', context.get('user_query', ''))
            formatted += f"\n### Query {idx}: {query}\n"

            clarified_qa = context.get('clarified Q&A', context.get('clarified_qa', []))
            if clarified_qa:
                formatted += "Clarifying Questions & Answers:\n"
                for q in clarified_qa:
                    formatted += f"  - Q{q.get('id', '')} [{q.get('category', 'N/A')}]: {q.get('question', '')}\n"
                    formatted += f"    Answer: {q.get('answer', 'No answer provided')}\n"

    # 2. User travel persona
    persona = intent_data.get('user_travel_persona', '')
    if persona:
        formatted += f"\n## User Travel Persona:\n{persona}\n"

    # 3. Travel intent
    travel_intent = intent_data.get('travel_intent', '')
    if travel_intent:
        formatted += f"\n## Travel Intent:\n{travel_intent}\n"

    # 4. Compromise details
    compromise = intent_data.get('compromise', {})
    if compromise:
        formatted += "\n## Compromise Flexibility:\n"
        willing = compromise.get('willing_to_compromise', False)
        formatted += f"Willing to compromise: {'Yes' if willing else 'No'}\n"

        factors = compromise.get('compromise_factors', [])
        if factors:
            formatted += f"Compromise factors: {', '.join(factors)}\n"

    formatted += "\n=== End of Context ===\n\n"
    return formatted


def inject_to_llm_request(text: str, llm_request: LlmRequest):
    # Inject into the LLM request
    if llm_request.contents and len(llm_request.contents) > 0:
        # Find the last user message
        for content in reversed(llm_request.contents):
            if content.role == 'user':
                # Prepend clarification data to the existing user message
                data_part = types.Part(text=text)

                # Insert at the beginning of the parts list
                if content.parts:
                    content.parts.insert(0, data_part)
                else:
                    content.parts = [data_part]

                print(f"[Callback] Injected clarification data into user message.")
                break

    return llm_request
