from google.adk.agents.llm_agent import Agent
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv
import os
from functools import partial
from backend.adk.tools.recsys import recsys_callback

load_dotenv()

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "../../../prompts/")
ENV = Environment(loader=FileSystemLoader(PROMPT_DIR))

from backend.schema.schema import RecsysOutput


async def get_recsys_agent(has_context: bool = False):
    if has_context:
        template = ENV.get_template("rec_with_context.jinja2")
    else:
        template = ENV.get_template("rec_baseline.jinja2")
    # Create callback with has_context bound to it
    callback_with_context = partial(recsys_callback, has_context=has_context)

    recsys_agent = Agent(
        model='gemini-2.5-flash',
        name='recsys',
        description='An agent that generates travel recommendations for city trips, given an user query.',
        instruction=template.render(),
        output_schema=RecsysOutput,
        before_model_callback=callback_with_context
    )
    return recsys_agent
