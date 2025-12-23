from google.adk.agents.llm_agent import Agent
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv
import os

load_dotenv()
from pydantic import BaseModel, Field
from typing import List, Literal

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "../../../prompts/")
ENV = Environment(loader=FileSystemLoader(PROMPT_DIR))

class ClarifyingQuestion(BaseModel):
    q_id: int = Field(..., description="A unique integer ID for the question.")
    q_category: Literal[
        "disambiguation",
        "preference_personal",
        "preference_spatial",
        "preference_temporal",
        "preference_purpose",
        "topic",
        "comparison_sustainability"
    ] = Field(..., description="The category classification of the clarifying question.")
    clarify_q: str = Field(..., description="The actual text of the clarifying question.")

class CQOutput(BaseModel):
    query: str = Field(..., description="The original user query being clarified.")
    clarifying_questions: List[ClarifyingQuestion] = Field(
        ...,
        description="A list of generated clarifying questions to refine the user's intent."
    )

async def get_cq_agent():
    cq_template = ENV.get_template("clarifying_questions.jinja2")

    clarifyingQuestionGenerator = Agent(
        model='gemini-2.5-flash',
        name='clarifying_question_generator',
        description='An agent that generates clarifying questions, given an user query.',
        instruction=cq_template.render(),
        output_schema=CQOutput,
        # instruction=template,
    )
    return clarifyingQuestionGenerator
