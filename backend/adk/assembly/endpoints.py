from fastapi import APIRouter, HTTPException

from backend.adk.agents.clar_q_gen.agent import CQOutput
from backend.adk.agents.clar_q_gen.cq_generator import generate_clarifying_questions
# Create a router for user endpoints
router = APIRouter(tags=["users"])


@router.get("/users/")
async def read_users():
    return [{"username": "Rick"}, {"username": "Morty"}]


@router.post("/clarify", response_model=CQOutput)
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

