from __future__ import annotations
from typing import Optional, List, Union
from pydantic import BaseModel, Field

from backend.schema.intentClassifier import IntentClassificationOutput
from backend.schema.recSys import RecommendationContext


class CFEContext(BaseModel):
    """
    Complete context for CFE agent including intent classification and both recommendations.
    """
    intent_classification: Optional[IntentClassificationOutput] = Field(
        None,
        description="Intent classification output containing user queries, clarifying Q&A, travel persona, and compromise details"
    )
    baseline_recommendation: Optional[RecommendationContext] = Field(
        None,
        description="Baseline recommendation without context"
    )
    context_aware_recommendation: Optional[RecommendationContext] = Field(
        None,
        description="Context-aware recommendation with intent classification"
    )


class CFEOutput(BaseModel):
    session_id: str = Field(
        ...,
        description="Unique identifier for the recommendation session"
    )
    user_query: str = Field(..., description="The original user query")
    context: Optional[CFEContext] = Field(
        None,
        description="Complete context including intent classification, baseline and context-aware recommendations with their explanations"
    )
    recommendation_shown: Union[str, List[str]] = Field(
        ...,
        description="Final recommended city or list of cities after CFE analysis"
    )

    explanation_shown: str = Field(
        ...,
        description="Comprehensive explanation for the final recommendation", 
        # max_length=1000
    )
    
    alternative_recommendation: Optional[List[str]] = Field(
        None,
        description="Alternative recommendation which was not shown to the user"
    )

    alternative_explanation: Optional[str] = Field(
        None,
        description="Explanation for the alternative recommendation"
    )
    time_taken_seconds: Optional[float] = Field(
        None,
        description="Total time taken in seconds to generate the CFE response"
    )
    db_ingestion_status: bool = Field(
        default=False,
        description="Status indicating whether the CFE response was successfully ingested into the database."
    )