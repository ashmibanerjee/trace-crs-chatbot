import asyncio
import os
import time

from fastapi import APIRouter, Header, HTTPException
from typing import Optional
import datetime
from backend.adk.agents.cfe.agent import get_cfe_agent
from backend.adk.agents.intent_classification.agent import get_ic_agent
from backend.adk.agents.recsys.agent import get_recsys_agent
from backend.adk.assembly.pipeline import get_root_agent
from backend.adk.assembly.run import _call_agent_async, get_model_response
from backend.schema.cfe import CFEOutput, CFEContext
from backend.schema.recSys import RecsysOutput, RecommendationContext
from backend.schema.intentClassifier import IntentClassificationOutput
from backend.schema.cqGen import CQOutput
from backend.adk.agents.clar_q_gen.cq_generator import generate_clarifying_questions
import json
from utils.firestore_utils import ingest_response_firestore, get_firestore_client

router = APIRouter(tags=["ADK Endpoints"])

# Serialize concurrent requests that swap GOOGLE_API_KEY — acceptable for a demo
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


# ---------------------------------------------------------------------------
# Clarifying questions
# ---------------------------------------------------------------------------

@router.post("/generate-clarifying-questions", response_model=CQOutput)
async def get_clarifying_questions(
    user_input: str,
    x_model_provider: str = Header(default="gemma", alias="X-Model-Provider"),
    x_api_key: Optional[str] = Header(default=None, alias="X-Api-Key"),
):
    """Step 1: generate clarifying questions for a user query."""
    try:
        if x_model_provider == "gemma":
            from backend.llm.gemma_pipeline import generate_cq
            return await generate_cq(user_input)

        # Gemini path
        async def _gemini():
            return await generate_clarifying_questions(user_input)

        return await _with_gemini_key(_gemini(), x_api_key)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Intent classifier (standalone endpoint — called only from Gemini path)
# ---------------------------------------------------------------------------

@router.get("/intent-classifier", response_model=IntentClassificationOutput)
async def get_intent_classifier_response(
    session_id: str,
    x_model_provider: str = Header(default="gemini", alias="X-Model-Provider"),
    x_api_key: Optional[str] = Header(default=None, alias="X-Api-Key"),
):
    try:
        async def _gemini():
            model_init = await get_ic_agent()
            agent_name, response_text = None, None
            async for name, text in _call_agent_async(
                query=f"[SESSION_ID:{session_id}]",
                root_agent=model_init,
                session_id=session_id,
            ):
                agent_name, response_text = name, text

            response = json.loads(response_text)
            response["session_id"] = session_id
            ingestion_success = await ingest_response_firestore(
                "intent_classifier_responses", session_id, response
            )
            response["db_ingestion_status"] = ingestion_success
            return IntentClassificationOutput(**response)

        return await _with_gemini_key(_gemini(), x_api_key)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Recommender (standalone — called only from Gemini path)
# ---------------------------------------------------------------------------

@router.get("/recommender-output", response_model=RecsysOutput)
async def get_recommender_response(
    session_id: str,
    has_context: bool = True,
    x_model_provider: str = Header(default="gemini", alias="X-Model-Provider"),
    x_api_key: Optional[str] = Header(default=None, alias="X-Api-Key"),
):
    try:
        async def _gemini():
            if has_context:
                model_init = await get_recsys_agent(has_context=True)
                collection_name = "context_aware_recommendations"
            else:
                model_init = await get_recsys_agent(has_context=False)
                collection_name = "baseline_recommendations"

            agent_name, response_text = None, None
            async for name, text in _call_agent_async(
                query=f"[SESSION_ID:{session_id}]",
                root_agent=model_init,
                session_id=session_id,
            ):
                agent_name, response_text = name, text

            if not response_text or not response_text.strip():
                raise HTTPException(status_code=502, detail="Empty response from recommendation agent")

            response = json.loads(response_text)
            ingestion_success = await ingest_response_firestore(collection_name, session_id, response)
            response["db_ingestion_status"] = ingestion_success
            return RecsysOutput(**response)

        return await _with_gemini_key(_gemini(), x_api_key)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# CFE (standalone — called only from Gemini path)
# ---------------------------------------------------------------------------

@router.get("/cfe-output", response_model=CFEOutput)
async def get_cfe_response(
    session_id: str,
    x_model_provider: str = Header(default="gemini", alias="X-Model-Provider"),
    x_api_key: Optional[str] = Header(default=None, alias="X-Api-Key"),
):
    try:
        async def _gemini():
            model_init = await get_cfe_agent()
            agent_name, response_text = None, None
            async for name, text in _call_agent_async(
                query=f"[SESSION_ID:{session_id}]",
                root_agent=model_init,
                session_id=session_id,
            ):
                agent_name, response_text = name, text

            response = json.loads(response_text)
            ingestion_success = await ingest_response_firestore("cfe_responses", session_id, response)
            response["db_ingestion_status"] = ingestion_success
            return CFEOutput(**response)

        return await _with_gemini_key(_gemini(), x_api_key)

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Full pipeline (main entry point called by the frontend)
# ---------------------------------------------------------------------------

@router.get("/run-pipeline", response_model=CFEOutput)
async def run_pipeline(
    session_id: str,
    x_model_provider: str = Header(default="gemma", alias="X-Model-Provider"),
    x_api_key: Optional[str] = Header(default=None, alias="X-Api-Key"),
):
    try:
        start_time = time.time()

        if x_model_provider == "gemma":
            from backend.llm.gemma_pipeline import run_full_pipeline as gemma_run
            cfe_output = await gemma_run(session_id)
            cfe_output.time_taken_seconds = time.time() - start_time
            return cfe_output

        # Gemini path
        async def _gemini():
            model_init = await get_root_agent()
            result = await get_model_response(
                query=f"[USER QUERY]: {session_id}]",
                root_agent=model_init,
                session_id=session_id,
                return_cfe_only=True,
            )
            if result is None:
                raise HTTPException(status_code=404, detail="CFE response not found in pipeline")
            result.time_taken_seconds = time.time() - start_time

            response_dict = result.model_dump()
            ingestion_success = await ingest_response_firestore(
                "cfe_pipeline_responses", session_id, response_dict
            )
            result.db_ingestion_status = ingestion_success
            return result

        return await _with_gemini_key(_gemini(), x_api_key)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/run-pipeline-all-responses")
async def run_pipeline_all_responses(session_id: str):
    try:
        model_init = await get_root_agent()
        all_responses = await get_model_response(
            query=f"[SESSION_ID:{session_id}]",
            root_agent=model_init,
            session_id=session_id,
            return_cfe_only=False,
        )
        return {"session_id": session_id, "responses": all_responses}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
