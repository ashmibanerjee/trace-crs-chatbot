from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from backend.schema.cqGen import ClarifyingQuestion


class InputContext(BaseModel):
    """
    Represents one interaction block containing the query and associated Q&A.
    """
    user_query: str = Field(
        ...,
        alias="user query",
        description="The initial query provided by the user."
    )
    clarified_qa: List[ClarifyingQuestion] = Field(
        ...,
        alias="clarified Q&A",
        description="List of clarifying questions and answers associated with this query."
    )


class CompromiseDetails(BaseModel):
    """
    Breakdown of the user's willingness to compromise.
    """
    willing_to_compromise: bool = Field(
        ...,
        description="True if the user indicates flexibility or willingness to change plans."
    )
    compromise_factors: List[str] = Field(
        default_factory=list,
        description="Specific list of factors the user is willing to compromise on (e.g., ['budget', 'travel dates', "
                    "'airline'])."
    )


class IntentClassificationOutput(BaseModel):
    session_id: str = Field(
        ...,
        description="Unique identifier for the session this intent classification belongs to."
    )
    input_data: List[InputContext] = Field(
        ...,
        alias="input",
        description="A history of the user's queries and the resulting clarified Q&A contexts."
    )
    user_travel_persona: str = Field(
        ...,
        description="A synthesized summary of the user's travel preferences, likes, and dislikes based on the input."
    )
    travel_intent: str = Field(
        ...,
        description="The specific goal or intention of the user's trip (e.g., 'Business trip with leisure', "
                    "'Budget backpacking')."
    )
    compromise: CompromiseDetails = Field(
        ...,
        description="Analysis of whether the user allows flexibility and on which specific aspects."
    )
    db_ingestion_status: bool = Field(
        default=False,
        description="Status indicating whether the intent classification response was successfully ingested into the database."
    )
