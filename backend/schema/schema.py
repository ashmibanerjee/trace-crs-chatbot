from typing import Literal, Optional, List

from pydantic import BaseModel, Field


class ClarifyingQuestion(BaseModel):
    id: int = Field(..., description="A unique integer ID for the question.")
    category: Literal[
        "disambiguation",
        "preference_personal",
        "preference_spatial",
        "preference_temporal",
        "preference_purpose",
        "topic",
        "comparison_sustainability"
    ] = Field(..., description="The category classification of the clarifying question.")
    question: str = Field(..., description="The actual text of the clarifying question.")
    answer: Optional[str] = Field(None, description="The answer to the clarifying question, if available.")


class CQOutput(BaseModel):
    query: str = Field(..., description="The original user query being clarified.")
    clarifying_questions: List[ClarifyingQuestion] = Field(
        ...,
        description="A list of generated clarifying questions to refine the user's intent."
    )


class RecBaselineOutput(BaseModel):
    query: str
    city: str
    explanation: str