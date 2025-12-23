from google.adk.agents.llm_agent import Agent
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv

load_dotenv()
from pydantic import BaseModel, Field
from typing import List, Literal

PROMPT_DIR = "../../../prompts/"
ENV = Environment(loader=FileSystemLoader(PROMPT_DIR))

# TODO : Define output schema
async def get_ic_agent():
    cq_template = ENV.get_template("intent_classification.jinja2")

    intentClassifierAgent = Agent(
        model='gemini-2.5-flash',
        name='intent_classification',
        description='An agent that generates intents from the user query + clarifying questions.',
        instruction=cq_template.render(),
        output_schema=None,
        # instruction=template,
    )
    return intentClassifierAgent
