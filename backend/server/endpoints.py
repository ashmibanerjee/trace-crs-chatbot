from fastapi import APIRouter, HTTPException

from backend.adk.agents.cfe.agent import get_cfe_agent
from backend.adk.agents.intent_classification.agent import get_ic_agent
from backend.adk.agents.recsys.agent import get_recsys_agent
from backend.adk.assembly.run import call_agent_async
from backend.schema.schema import CQOutput, RecsysOutput, IntentClassificationOutput, CFEOutput, CFEContext, RecommendationContext
from backend.adk.agents.clar_q_gen.cq_generator import generate_clarifying_questions
import json
from utils.firestore_utils import ingest_response_firestore, get_firestore_client

# Create a router for user endpoints
router = APIRouter(tags=["ADK Endpoints"])


@router.post("/generate-clarifying-questions", response_model=CQOutput)
async def get_clarifying_questions(user_input: str):
    """
    Step 1: Frontend sends query, Backend returns clarifying questions.
    """
    try:
        print(f"Received user input for clarification: {user_input}")
        # Placeholder for actual agent call
        responses = await generate_clarifying_questions(user_input)
        return responses

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/intent-classifier", response_model=IntentClassificationOutput)
async def get_intent_classifier_response(session_id: str):
    """
    Intent classifier endpoint that retrieves clarification data from Firestore

    Args:
        session_id: Session identifier to retrieve conversation with clarification data

    Returns:
        Intent classification result including user persona, travel intent, and compromises
    """
    try:
        print(f"[Intent Classifier API] Received request for session_id: {session_id}")

        # Initialize agent with callback
        model_init = await get_ic_agent()

        # Call agent with session_id embedded in query
        # The callback will extract session_id and retrieve clarification data
        agent_name, response = await call_agent_async(
            query=f"[SESSION_ID:{session_id}]",
            root_agent=model_init,
            session_id=session_id
        )

        response = json.loads(response)
        response['session_id'] = session_id

        print(f"[Intent Classifier API] Successfully classified intent for session {session_id}")
        ingestion_success = await ingest_response_firestore('intent_classifier_responses', session_id, response)
        if ingestion_success:
            print(f"[Intent Classifier API] Successfully ingested response for session {session_id}")
        else:
            print(f"[Intent Classifier API] Warning: Failed to ingest response for session {session_id}")

        response['db_ingestion_success'] = ingestion_success
        response_obj = IntentClassificationOutput(**response)
        return response_obj

    except Exception as e:
        print(f"[Intent Classifier API] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommender-output", response_model=RecsysOutput)
async def get_recommender_response(session_id: str, has_context: bool = True):
    try:
        print(f"[Recommender API] Received request for session_id: {session_id}")
        if not session_id:
            raise ValueError("Session ID is required for context-aware recommender")
        if has_context:
            model_init = await get_recsys_agent(has_context=True)
            collection_name = 'context_aware_recommendations'
        else:
            model_init = await get_recsys_agent(has_context=False)
            collection_name = 'baseline_recommendations'
        agent_name, response = await call_agent_async(
            query=f"[SESSION_ID:{session_id}]",
            root_agent=model_init,
            session_id=session_id
        )
        response = json.loads(response)
        ingestion_success = await ingest_response_firestore(collection_name, session_id, response)
        if ingestion_success:
            print(f"[Recommender API] Successfully ingested response for session {session_id}")
        else:
            print(f"[Recommender API] Warning: Failed to ingest response for session {session_id}")

        response['db_ingestion_status'] = ingestion_success
        response_obj = RecsysOutput(**response)
        return response_obj
    except Exception as e:
        print(f"[Recommender API] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cfe-output", response_model=CFEOutput)
async def get_cfe_response(session_id: str):
    """
    CFE (Counterfactual Explanation) endpoint that combines baseline and context-aware
    recommendations with intent classification to generate a comprehensive explanation.
    
    Args:
        session_id: Session identifier to retrieve all recommendation data
        
    Returns:
        CFE output with complete context including intent classification and both recommendations
    """
    try:
        print(f"[CFE API] Received request for session_id: {session_id}")
        
        if not session_id:
            raise ValueError("Session ID is required for CFE generation")

        model_init = await get_cfe_agent()
        agent_name, response = await call_agent_async(
            query=f"[SESSION_ID:{session_id}]",
            root_agent=model_init,
            session_id=session_id
        )
        response = json.loads(response)
        ingestion_success = await ingest_response_firestore("cfe_responses", session_id, response)
        if ingestion_success:
            print(f"[Recommender API] Successfully ingested response for session {session_id}")
        else:
            print(f"[Recommender API] Warning: Failed to ingest response for session {session_id}")

        response['db_ingestion_status'] = ingestion_success
        response_obj = CFEOutput(**response)
        return response_obj
        
    except Exception as e:
        print(f"[CFE API] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
