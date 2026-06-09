"""
Gemma pipeline: replicates the ADK multi-agent pipeline using the HF Inference API.

Data flow (mirrors the ADK SequentialAgent + ParallelAgent structure):
  1. generate_cq(query)          → CQOutput
  2. run_full_pipeline(session):
       a. read clarification data from store
       b. intent_classifier           (sequential)
       c. baseline_recsys + ca_recsys (parallel)
       d. cfe_agent                   (combines all three)
"""
import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, Field

from backend.llm.hf_runner import call_structured
from backend.schema.cfe import CFEOutput
from backend.schema.cqGen import ClarifyingQuestion, CQOutput
from backend.adk.tools.utils import format_clarification_as_text, format_intent_context_as_text
from constants import CITIES

logger = logging.getLogger(__name__)

_PROMPT_DIR = Path(__file__).parent.parent / "prompts"
_ENV = Environment(loader=FileSystemLoader(str(_PROMPT_DIR)))


# ---------------------------------------------------------------------------
# Lightweight intermediate schemas (no aliases — easier for Gemma to follow)
# ---------------------------------------------------------------------------

class _Compromise(BaseModel):
    willing_to_compromise: bool
    compromise_factors: List[str] = Field(default_factory=list)


class _ICOutput(BaseModel):
    user_travel_persona: str
    travel_intent: str
    compromise: _Compromise


class _RecOutput(BaseModel):
    recommendation: Any  # str or list[str]
    explanation: str
    trade_off: Optional[str] = None


# Simpler CQ schema for Gemma — omits the optional `answer` field which confuses the model
class _CQQuestion(BaseModel):
    id: int
    question: str


class _CQOutput(BaseModel):
    query: str
    clarifying_questions: List[_CQQuestion]


async def _fs_set(collection: str, session_id: str, data: Dict[str, Any]) -> None:
    """Best-effort Firestore write for intermediate pipeline outputs (IC, RecSys, CFE)."""
    try:
        from utils.firestore_utils import ingest_response_firestore
        await ingest_response_firestore(collection, session_id, data)
    except Exception as exc:
        logger.warning("[Gemma] Firestore write skipped (%s/%s): %s", collection, session_id, exc)


# ---------------------------------------------------------------------------
# Individual pipeline steps
# ---------------------------------------------------------------------------

_SCOPE_KEYWORDS = {
    "city", "europe", "european", "trip", "travel", "holiday", "vacation",
    "visit", "destination", "recommend", "suggest", "where", "break",
    "weekend", "tourism", "tour", "country",
}

# Minimal fallback questions used when the model fails or incorrectly rejects a travel query
_FALLBACK_QUESTIONS = [
    ClarifyingQuestion(
        id=1,
        question="What is your approximate budget for this trip (e.g. budget, mid-range, or luxury)?",
    ),
    ClarifyingQuestion(
        id=2,
        question=(
            "Would you be open to a less well-known destination if it matched your interests "
            "and had fewer crowds (a more sustainable choice)?"
        ),
    ),
]


def _looks_like_travel_query(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kw in _SCOPE_KEYWORDS)


async def generate_cq(query: str) -> CQOutput:
    """Step 0 (called by /generate-clarifying-questions): produce clarifying questions."""
    system_prompt = _ENV.get_template("cqs_variant1.jinja2").render()
    data: Optional[Dict[str, Any]] = None
    try:
        data = await call_structured(
            system_prompt=system_prompt,
            user_message=f"User query: {query}",
            schema=_CQOutput,  # simpler schema — no answer field to confuse the model
            max_tokens=1500,
        )
    except Exception as exc:
        logger.warning("[Gemma] CQ generation failed ('%s'): %s", query[:80], exc)

    if data is not None:
        data.setdefault("query", query)
        raw_qs = data.get("clarifying_questions", [])
        questions = [ClarifyingQuestion(id=q["id"], question=q["question"]) for q in raw_qs]
    else:
        questions = []

    # If the model returned an out-of-scope signal (id=-1) or nothing at all, but the
    # query looks like a legitimate travel request, use the fallback questions instead
    # of treating the user's query as out of scope.
    is_out_of_scope_signal = (
        not questions
        or (len(questions) == 1 and questions[0].id == -1)
    )
    if is_out_of_scope_signal:
        if _looks_like_travel_query(query):
            logger.warning(
                "[Gemma] Model returned no/invalid questions for travel query '%s'. "
                "Using fallback questions.", query[:80]
            )
            questions = _FALLBACK_QUESTIONS
        else:
            # Genuinely out of scope — return id=-1 so the middleware shows the right message
            questions = [ClarifyingQuestion(id=-1, question="")]

    query_text = data["query"] if data else query
    return CQOutput(query=query_text, clarifying_questions=questions)


async def _run_ic(clarification_data: Dict[str, Any]) -> Dict[str, Any]:
    system_prompt = _ENV.get_template("intent_classification.jinja2").render()
    context_text = format_clarification_as_text(clarification_data)
    return await call_structured(
        system_prompt=system_prompt,
        user_message=context_text,
        schema=_ICOutput,
        max_tokens=2000,
    )


async def _run_baseline_recsys(query: str) -> Dict[str, Any]:
    system_prompt = _ENV.get_template("rec_baseline.jinja2").render(city_catalog=CITIES)
    return await call_structured(
        system_prompt=system_prompt,
        user_message=f"User query: {query}",
        schema=_RecOutput,
        max_tokens=1000,
    )


async def _run_ca_recsys(query: str, ic_data: Dict[str, Any]) -> Dict[str, Any]:
    system_prompt = _ENV.get_template("rec_with_context.jinja2").render(city_catalog=CITIES)
    intent_context = format_intent_context_as_text(ic_data)
    return await call_structured(
        system_prompt=system_prompt,
        user_message=f"User query: {query}\n\n{intent_context}",
        schema=_RecOutput,
        max_tokens=1000,
    )


def _format_cfe_context(ic_data: Dict, ca_data: Dict, baseline_data: Dict) -> str:
    import json
    ctx = {
        "intent_classification": ic_data,
        "baseline_recommendation": {
            "recommendation": baseline_data.get("recommendation"),
            "explanation": baseline_data.get("explanation"),
            "trade_off": baseline_data.get("trade_off"),
        },
        "context_aware_recommendation": {
            "recommendation": ca_data.get("recommendation"),
            "explanation": ca_data.get("explanation"),
            "trade_off": ca_data.get("trade_off"),
        },
    }
    return (
        "=== CONTEXT DATA (Include this in your 'context' field) ===\n"
        + json.dumps(ctx, indent=2)
        + "\n=== END CONTEXT DATA ==="
    )


async def _run_cfe(session_id: str, query: str, ic_data: Dict, ca_data: Dict, baseline_data: Dict) -> Dict[str, Any]:
    system_prompt = _ENV.get_template("cfe_combination.jinja2").render()
    context_text = _format_cfe_context(ic_data, ca_data, baseline_data)
    user_message = f"Session ID: {session_id}\nUser query: {query}\n\n{context_text}"
    data = await call_structured(
        system_prompt=system_prompt,
        user_message=user_message,
        schema=CFEOutput,
        max_tokens=2500,
    )
    # Inject required fields the model might omit
    data.setdefault("session_id", session_id)
    data.setdefault("user_query", query)
    data.setdefault("db_ingestion_status", False)
    return data


# ---------------------------------------------------------------------------
# Full pipeline entry point
# ---------------------------------------------------------------------------

async def run_full_pipeline(session_id: str) -> CFEOutput:
    """
    Run the complete Gemma pipeline for a session whose clarification data is
    already stored (written by the middleware orchestrator via the conversation store).
    """
    from database.config import get_conversation_store
    conv_store = get_conversation_store()
    conv_data = await conv_store.get_conversation(session_id)

    if not conv_data:
        raise ValueError(f"No conversation data found for session '{session_id}'")

    clarification_data = conv_data.get("clarification_data") or conv_data
    query = clarification_data.get("query", "")

    logger.info("[Gemma] Running pipeline for session %s, query: %.80s", session_id, query)

    # Step 1: Intent classification
    ic_data = await _run_ic(clarification_data)
    ic_store = {**ic_data, "session_id": session_id, "db_ingestion_status": False}
    await _fs_set("intent_classifier_responses", session_id, ic_store)

    # Step 2: Baseline RecSys and CA RecSys in parallel
    baseline_data, ca_data = await asyncio.gather(
        _run_baseline_recsys(query),
        _run_ca_recsys(query, ic_data),
    )
    await asyncio.gather(
        _fs_set("baseline_recommendations", session_id, {**baseline_data, "session_id": session_id}),
        _fs_set("context_aware_recommendations", session_id, {**ca_data, "session_id": session_id}),
    )

    # Step 3: CFE
    cfe_data = await _run_cfe(session_id, query, ic_data, ca_data, baseline_data)
    await _fs_set("cfe_pipeline_responses", session_id, cfe_data)

    return CFEOutput.model_validate(cfe_data)
