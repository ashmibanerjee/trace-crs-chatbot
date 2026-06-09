"""
Orchestrator Middleware
Connects Chainlit frontend to backend agents.
model_provider ("gemma" | "gemini") and api_key are forwarded from the Chainlit session
to the backend via HTTP headers on every request.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from config import settings
from database.config import get_session_store, get_conversation_store
from middleware.clarification_handler import ClarificationHandler, ClarificationState


class SessionManager:
    def __init__(self):
        self.store = get_session_store()
        self.timeout = settings.session_timeout
        self.max_history = settings.max_conversation_history

    async def get_or_create_session(self, session_id: str) -> Dict[str, Any]:
        session = await self.store.get_session(session_id)
        if session is None:
            session = await self.store.create_session(session_id, {
                "collected_entities": {},
                "conversation_history": [],
            })
        return session

    async def update_session(self, session_id: str, updates: Dict[str, Any]):
        await self.store.update_session(session_id, updates)

    async def clear_session(self, session_id: str):
        await self.store.delete_session(session_id)


class ConversationOrchestrator:
    """
    Main orchestrator that connects frontend to backend.
    model_provider and api_key thread through every method that touches the backend.
    """

    def __init__(self):
        self.session_manager = SessionManager()
        self.clarification_handler = ClarificationHandler()
        self.conversation_store = get_conversation_store()

    # ------------------------------------------------------------------
    # Public entry points — both accept model_provider / api_key
    # ------------------------------------------------------------------

    async def process_message(
        self,
        message: str,
        session_id: str,
        user_context: Optional[Dict[str, Any]] = None,
        model_provider: str = "gemma",
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        print(f"[ORCHESTRATOR] Processing message with session_id: {session_id}")
        session_state = await self.session_manager.get_or_create_session(session_id)
        print(f"[ORCHESTRATOR] Session has {len(session_state.get('conversation_history', []))} messages in history")

        if session_state.get("clarification_complete") and not self.is_clarification_active(session_state):
            session_state["clarification_complete"] = False
            session_state["clarification_state"] = None
            session_state["original_clarification_query"] = None
            if "collected_entities" in session_state:
                session_state["collected_entities"].pop("clarification_answers", None)
            await self.session_manager.update_session(session_id, session_state)

        if self.is_clarification_active(session_state):
            return await self.handle_clarification_answer(message, session_id)

        if self.should_trigger_clarification(message, session_state):
            return await self.start_clarification_flow(
                message, session_id, model_provider=model_provider, api_key=api_key
            )

        return {
            "text": "Thank you for your message. This is currently out of my scope.",
            "elements": [],
            "actions": [],
            "metadata": {},
        }

    async def call_run_pipeline(
        self,
        session_id: str,
        model_provider: str = "gemma",
        api_key: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Run the recommendation pipeline by calling backend functions directly."""
        import logging
        import traceback
        from middleware.clarification_handler import _with_gemini_key
        try:
            if model_provider == "gemma":
                from backend.llm.gemma_pipeline import run_full_pipeline
                print(f"[Orchestrator] Running Gemma pipeline for session {session_id}")
                result = await run_full_pipeline(session_id)
                return result.model_dump() if hasattr(result, "model_dump") else result

            # Gemini path
            import time
            from backend.adk.assembly.pipeline import get_root_agent
            from backend.adk.assembly.run import get_model_response

            async def _gemini():
                start = time.time()
                model_init = await get_root_agent()
                result = await get_model_response(
                    query=f"[USER QUERY]: {session_id}]",
                    root_agent=model_init,
                    session_id=session_id,
                    return_cfe_only=True,
                )
                if result is None:
                    raise ValueError("CFE response not found in pipeline")
                result.time_taken_seconds = time.time() - start
                return result.model_dump() if hasattr(result, "model_dump") else result

            return await _with_gemini_key(_gemini(), api_key)

        except Exception as e:
            logging.error(f"Error running pipeline: {e}")
            traceback.print_exc()
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # Clarification flow helpers
    # ------------------------------------------------------------------

    def _add_to_history(self, session_state, role, content, metadata=None):
        session_state["conversation_history"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        })

    async def _update_and_save_session(self, session_id, session_state):
        await self.session_manager.update_session(session_id, session_state)
        await self._save_conversation(session_id, session_state)

    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        return {
            "text": f"⚠️ I encountered an error: {error_message}\n\nPlease try again or rephrase your question.",
            "elements": [],
            "actions": [],
            "metadata": {"error": True},
        }

    async def handle_action(self, action_name, action_value, session_id) -> Dict[str, Any]:
        if action_name == "quick_reply":
            return await self.process_message(message=str(action_value), session_id=session_id)
        elif action_name == "reset":
            await self.session_manager.clear_session(session_id)
            return {"text": "Conversation reset! Let's start fresh.", "elements": [], "actions": []}
        return {"text": f"Action '{action_name}' received.", "elements": [], "actions": []}

    async def _save_conversation(self, session_id, session_state):
        try:
            existing = await self.conversation_store.get_conversation(session_id)

            clarification_data = None
            clarification_complete = session_state.get("clarification_complete", False)
            clarification_state_dict = session_state.get("clarification_state")

            if clarification_state_dict:
                clarification_data = {
                    "query": clarification_state_dict.get("original_query", ""),
                    "clarifying_questions": clarification_state_dict.get("questions", []),
                    "clarification_complete": clarification_complete,
                }
            elif session_state.get("clarification_complete"):
                answers = session_state.get("collected_entities", {}).get("clarification_answers", {})
                if answers:
                    questions_with_answers = [
                        {
                            "id": int(q_id),
                            "question": ans_data.get("question", ""),
                            "answer": ans_data.get("answer", ""),
                        }
                        for q_id, ans_data in sorted(answers.items(), key=lambda x: int(x[0]))
                    ]
                    clarification_data = {
                        "query": session_state.get("original_clarification_query", ""),
                        "clarifying_questions": questions_with_answers,
                        "clarification_complete": True,
                    }

            update_data = {"conversation_history": session_state["conversation_history"]}
            if clarification_data:
                update_data["clarification_data"] = clarification_data

            if existing:
                await self.conversation_store.update_conversation(session_id, update_data)
            else:
                conversation_data = {"conversation_history": session_state["conversation_history"]}
                if clarification_data:
                    conversation_data["clarification_data"] = clarification_data
                await self.conversation_store.create_conversation(session_id, conversation_data)

        except Exception as e:
            import logging
            logging.error(f"Error saving conversation {session_id}: {e}")

    async def start_clarification_flow(
        self,
        query: str,
        session_id: str,
        model_provider: str = "gemma",
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        session_state = await self.session_manager.get_or_create_session(session_id)

        clarification_state = await self.clarification_handler.generate_questions(
            query, model_provider=model_provider, api_key=api_key
        )

        if not clarification_state:
            self._add_to_history(session_state, "user", query, {"type": "out_of_scope_query"})
            self._add_to_history(
                session_state, "assistant",
                "Query is beyond the scope of European city recommendation.",
                {"type": "out_of_scope_response"},
            )
            await self._save_conversation(session_id, session_state)

            session_state.update({
                "clarification_state": None,
                "clarification_complete": False,
                "original_clarification_query": None,
            })
            if "collected_entities" in session_state:
                session_state["collected_entities"].pop("clarification_answers", None)
            await self.session_manager.update_session(session_id, session_state)
            return self.clarification_handler.format_out_of_scope()

        session_state["clarification_state"] = clarification_state.to_dict()
        session_state["original_clarification_query"] = query
        self._add_to_history(
            session_state, "user", query,
            {"type": "clarification_trigger", "total_questions": len(clarification_state.questions)},
        )
        await self._update_and_save_session(session_id, session_state)
        return self.clarification_handler.format_question_for_ui(clarification_state)

    async def handle_clarification_answer(self, answer: str, session_id: str) -> Dict[str, Any]:
        session_state = await self.session_manager.get_or_create_session(session_id)
        state_dict = session_state.get("clarification_state")
        if not state_dict:
            return self._create_error_response("No active clarification flow found")

        clarification_state = ClarificationState.from_dict(state_dict)
        current_question = clarification_state.get_current_question()
        if not current_question:
            return self._create_error_response("No current question found")

        clarification_state.add_answer(current_question["id"], answer)
        session_state["clarification_state"] = clarification_state.to_dict()

        if "clarification_answers" not in session_state["collected_entities"]:
            session_state["collected_entities"]["clarification_answers"] = {}
        session_state["collected_entities"]["clarification_answers"][str(current_question["id"])] = {
            "question": current_question["question"],
            "answer": answer,
        }

        self._add_to_history(
            session_state, "assistant", current_question["question"],
            {"type": "clarification_question", "question_id": current_question["id"]},
        )
        self._add_to_history(
            session_state, "user", answer,
            {"type": "clarification_answer", "question_id": current_question["id"]},
        )
        await self._update_and_save_session(session_id, session_state)

        if clarification_state.is_complete():
            session_state["clarification_state"] = None
            session_state["clarification_complete"] = True
            await self._update_and_save_session(session_id, session_state)

            response = self.clarification_handler.format_question_for_ui(clarification_state)
            response["summary"] = clarification_state.get_summary()
            response["trigger_pipeline"] = True
            return response
        else:
            return self.clarification_handler.format_question_for_ui(clarification_state)

    async def get_clarification_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        session_state = await self.session_manager.get_or_create_session(session_id)
        state_dict = session_state.get("clarification_state")
        if not state_dict:
            return session_state.get("collected_entities", {}).get("clarification_answers")
        return ClarificationState.from_dict(state_dict).get_summary()

    def is_clarification_active(self, session_state: Dict[str, Any]) -> bool:
        state_dict = session_state.get("clarification_state")
        if not state_dict:
            return False
        return not ClarificationState.from_dict(state_dict).is_complete()

    def should_trigger_clarification(self, message: str, session_state: Dict[str, Any]) -> bool:
        if session_state.get("clarification_complete"):
            return False
        if self.is_clarification_active(session_state):
            return False
        if len(message.lower().strip()) < 5:
            return False
        destination_keywords = [
            "find", "suggest", "recommend", "looking for", "want to", "travel",
            "visit", "trip", "europe", "city", "place", "destination", "where",
            "going to", "planning", "holiday", "vacation", "tourism", "tour",
            "spain", "france", "italy", "germany", "country", "countries",
        ]
        return any(kw in message.lower() for kw in destination_keywords)


# Singleton instance
orchestrator = ConversationOrchestrator()
