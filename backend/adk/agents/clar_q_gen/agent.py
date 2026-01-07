from google.adk.agents.llm_agent import Agent
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv
import os

from backend.schema.schema import CQOutput

load_dotenv()

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "../../../prompts/")
ENV = Environment(loader=FileSystemLoader(PROMPT_DIR))


async def get_cq_agent():
    cq_template = ENV.get_template("cqs_variant1.jinja2")

    clarifyingQuestionGenerator = Agent(
        model='gemini-2.5-flash',
        name='clarifying_question_generator',
        description='An agent that generates clarifying questions, given an user query.',
        instruction=cq_template.render(),
        output_schema=CQOutput,
        # instruction=template,
    )
    return clarifyingQuestionGenerator
