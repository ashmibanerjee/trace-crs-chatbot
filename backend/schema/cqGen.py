from __future__ import annotations

from typing import Optional, List

from pydantic import BaseModel, Field


class ClarifyingQuestion(BaseModel):
    id: int = Field(..., description="A unique integer ID for the question.")
    question: str = Field(..., description="The actual text of the clarifying question.")
    answer: Optional[str] = Field(None, description="The answer to the clarifying question, if available.")


class CQOutput(BaseModel):
    query: str = Field(..., description="The original user query being clarified.")
    clarifying_questions: List[ClarifyingQuestion] = Field(
        ...,
        description="A list of generated clarifying questions to refine the user's intent."
    )
