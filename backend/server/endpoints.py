from fastapi import APIRouter, HTTPException

from backend.adk.agents.rec_baseline.agent import get_rec_baseline
from backend.adk.assembly.run import call_agent_async
from backend.schema.schema import CQOutput, RecBaselineOutput
from backend.adk.agents.clar_q_gen.cq_generator import generate_clarifying_questions
import json
# Create a router for user endpoints
router = APIRouter(tags=["ADK Endpoints"])


@router.post("/clarify-questions-gen", response_model=CQOutput)
async def get_clarifications(user_input: str):
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


@router.post("/rec-baseline", response_model=RecBaselineOutput)
async def get_rec_baseline_response(user_input: str):
    try:
        print(f"Received user input for clarification: {user_input}")
        # Placeholder for actual agent call
        model_init = await get_rec_baseline()
        agent_name, response = await call_agent_async(user_input, model_init)
        response = json.loads(response)
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
