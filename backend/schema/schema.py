from typing import Literal, Optional, List, Union, Annotated
from pydantic import BaseModel, Field, constr


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


class RecsysOutput(BaseModel):
    session_id: str = Field(
        ...,
        description="Unique identifier for the recommendation session"
    )
    user_query: str = Field(..., description="The original user query")
    context: Optional[List[InputContext]] = Field(
        None,
        description="List of user queries with their associated clarifying questions and answers"
    )
    recommendation: Union[str, List[str]] = Field(
        ...,
        description="Recommended city or list of cities if explicitly requested"
    )

    explanation: str = Field(
        ...,
        description="Brief justification of why the recommendation fits"
    )

    trade_off: Optional[str] = Field(
        None,
        description="Brief description of any trade-offs made, if applicable"
    )
    db_ingestion_status: bool = Field(
        default=False,
        description="Status indicating whether the recommendation response was successfully ingested into the database."
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
