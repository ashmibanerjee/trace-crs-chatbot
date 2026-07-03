"""
Clarification Question Handler
Manages the generation and collection of clarifying questions.
Backend functions are called directly (in-process) rather than via HTTP to avoid
self-call reliability issues in the single-process FastAPI+Chainlit setup.
"""
from typing import Dict, Any, List, Optional
import asyncio
import os


class ClarificationState:
    """Tracks the state of clarifying questions for a session"""

    def __init__(self, questions: List[Dict[str, Any]], original_query: str):
        self.original_query = original_query
        self.questions = questions
        self.answers = {}
        self.current_index = 0

    def get_current_question(self) -> Optional[Dict[str, Any]]:
        if self.current_index < len(self.questions):
            return self.questions[self.current_index]
        return None

    def add_answer(self, question_id: int, answer: str) -> bool:
        current_question = self.get_current_question()
        if not current_question or current_question["id"] != question_id:
            return False
        question_id_str = str(question_id)
        current_question["answer"] = answer
        self.answers[question_id_str] = {
            "question": current_question["question"],
            "answer": answer,
        }
        self.current_index += 1
        return True

    def is_complete(self) -> bool:
        return self.current_index >= len(self.questions)

    def get_progress(self) -> Dict[str, Any]:
        return {
            "answered": len(self.answers),
            "total": len(self.questions),
            "current_index": self.current_index,
            "percentage": int((len(self.answers) / len(self.questions)) * 100) if self.questions else 100,
        }

    def get_summary(self) -> Dict[str, Any]:
        return {
            "original_query": self.original_query,
            "total_questions": len(self.questions),
            "answers": self.answers,
            "complete": self.is_complete(),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_query": self.original_query,
            "questions": self.questions,
            "answers": {str(k): v for k, v in self.answers.items()},
            "current_index": self.current_index,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClarificationState":
        state = cls(
            questions=data.get("questions", []),
            original_query=data.get("original_query", ""),
        )
        state.answers = data.get("answers", {})
        state.current_index = data.get("current_index", 0)
        return state


_gemini_key_lock = asyncio.Lock()


_VERTEXAI_ENV_VARS = (
    "GOOGLE_GENAI_USE_VERTEXAI",
    "GOOGLE_GENAI_USE_ENTERPRISE",
    "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_CLOUD_LOCATION",
    "GOOGLE_APPLICATION_CREDENTIALS",
)


async def _with_gemini_key(coro, api_key: Optional[str]):
    """Run *coro* using a user-supplied Gemini API key.

    Temporarily sets GOOGLE_API_KEY and clears any Vertex AI env vars so that
    google-genai uses Gemini API key auth instead of Vertex AI credentials.
    """
    if not api_key:
        return await coro
    async with _gemini_key_lock:
        orig_api_key = os.environ.get("GOOGLE_API_KEY")
        orig_vertexai = {k: os.environ.pop(k, None) for k in _VERTEXAI_ENV_VARS}
        os.environ["GOOGLE_API_KEY"] = api_key
        try:
            return await coro
        finally:
            if orig_api_key is not None:
                os.environ["GOOGLE_API_KEY"] = orig_api_key
            else:
                os.environ.pop("GOOGLE_API_KEY", None)
            for k, v in orig_vertexai.items():
                if v is not None:
                    os.environ[k] = v


class ClarificationHandler:
    """
    Handles the flow of clarifying questions.
    Calls backend functions directly (in-process) to avoid HTTP self-call issues.
    """

    def __init__(self, backend_url_resolver=None):
        self.backend_url_resolver = backend_url_resolver  # kept for API compat, unused

    async def generate_questions(
        self,
        query: str,
        model_provider: str = "gemma",
        api_key: Optional[str] = None,
    ) -> Optional[ClarificationState]:
        """Generate clarifying questions by calling the pipeline function directly."""
        try:
            if model_provider == "gemma":
                from backend.llm.gemma_pipeline import generate_cq
                result = await generate_cq(query)
            else:
                from backend.adk.agents.clar_q_gen.cq_generator import generate_clarifying_questions
                result = await _with_gemini_key(
                    generate_clarifying_questions(query), api_key
                )

            if result is None:
                print(f"[ClarificationHandler] No result from CQ generator for: {query}")
                return None

            # result may be a CQOutput pydantic model or a dict
            if hasattr(result, "clarifying_questions"):
                questions = [q.model_dump() for q in result.clarifying_questions]
                original_query = result.query
            else:
                questions = result.get("clarifying_questions", [])
                original_query = result.get("query", query)

            if not questions or (len(questions) == 1 and questions[0].get("id") == -1):
                print(f"[ClarificationHandler] Query is out of scope: {query}")
                return None

            return ClarificationState(questions=questions, original_query=original_query)

        except Exception as e:
            import traceback
            print(f"[ClarificationHandler] Error generating questions: {e}")
            traceback.print_exc()
            # Re-raise API/auth errors so the caller can show the user a real error
            # message rather than silently treating it as out-of-scope.
            if model_provider == "gemini":
                raise
            return None

    def format_question_for_ui(self, state: ClarificationState) -> Dict[str, Any]:
        current_question = state.get_current_question()
        progress = state.get_progress()

        if not current_question:
            return self._format_completion(state)

        return {
            "type": "clarification_question",
            "text": current_question["question"],
            "question_id": current_question["id"],
            "progress": progress,
            "metadata": {"clarification_active": True},
        }

    def _format_completion(self, state: ClarificationState) -> Dict[str, Any]:
        return {
            "type": "clarification_complete",
            "text": (
                "✅ **All questions answered!**\n\n"
                "Thank you for providing that information. "
                "Let me now find the best recommendations for you based on your preferences."
            ),
            "summary": state.get_summary(),
            "metadata": {
                "clarification_active": False,
                "clarification_complete": True,
            },
        }

    def format_error(self, error_message: str) -> Dict[str, Any]:
        return {
            "type": "clarification_error",
            "text": "⚠️ Unable to generate clarifying questions: Out of scope",
            "metadata": {"clarification_active": False, "error": True},
        }

    def format_out_of_scope(self) -> Dict[str, Any]:
        return {
            "type": "out_of_scope",
            "text": (
                "I'm sorry, but this query is beyond the scope of European city recommendation. "
                "I can only help you find and recommend European cities based on your preferences.\n\n"
                "Please ask a new query about European cities to start again."
            ),
            "metadata": {
                "clarification_active": False,
                "out_of_scope": True,
                "reset_session": True,
            },
        }
