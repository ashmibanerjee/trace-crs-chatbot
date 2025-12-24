from google.adk.agents.llm_agent import Agent
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv
import os
load_dotenv()

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "../../../prompts/")
ENV = Environment(loader=FileSystemLoader(PROMPT_DIR))


from backend.schema.schema import RecBaselineOutput


async def get_rec_baseline():
    rec_template = ENV.get_template("rec_baseline.jinja2")

    recommenderBaseline = Agent(
        model='gemini-2.5-flash',
        name='recommender_baseline',
        description='An agent that generates travel recommendations for city trips, given an user query.',
        instruction=rec_template.render(),
        output_schema=RecBaselineOutput,
        # instruction=template,
    )
    return recommenderBaseline