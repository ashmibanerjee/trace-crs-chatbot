from __future__ import annotations

from typing import Optional, List, Union

from pydantic import BaseModel, Field, field_validator

from backend.schema.intentClassifier import IntentClassificationOutput
from constants import CITIES


class RecsysOutput(BaseModel):
    session_id: str = Field(
        ...,
        description="Unique identifier for the recommendation session"
    )
    user_query: str = Field(..., description="The original user query")
    context: Optional[List[IntentClassificationOutput]] = Field(
        None,
        description="List of intent classification outputs containing user queries, clarifying Q&A, travel persona, "
                    "and compromise details"
    )
    recommendation: Union[str, List[str]] = Field(
        ...,
        description="Recommended city or list of cities if explicitly requested"
    )

    explanation: str = Field(
        ...,
        description="Brief justification of why the recommendation fits",
        # max_length=500
    )

    trade_off: Optional[str] = Field(
        None,
        description="Brief description of any trade-offs made, if applicable"
    )
    db_ingestion_status: bool = Field(
        default=False,
        description="Status indicating whether the recommendation response was successfully ingested into the database."
    )

    @field_validator('recommendation')
    @classmethod
    def validate_cities(cls, v):
        """Validate that all recommended cities are in the CITIES list."""
        cities_to_check = [v] if isinstance(v, str) else v

        invalid_cities = [city for city in cities_to_check if city not in CITIES]

        if invalid_cities:
            raise ValueError(
                f"Invalid city/cities in recommendation: {', '.join(invalid_cities)}. "
                f"Must be one of the cities from the CITIES list."
            )

        return v


class RecommendationContext(BaseModel):
    """
    Represents a recommendation with its explanation and trade-offs.
    """
    recommendation: Union[str, List[str]] = Field(
        ...,
        description="Recommended city or list of cities"
    )
    explanation: str = Field(
        ...,
        description="Justification of why the recommendation fits",
        # max_length=1000
    )
    trade_off: Optional[str] = Field(
        None,
        description="Description of any trade-offs made, if applicable"
    )
