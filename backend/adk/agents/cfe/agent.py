from google.adk.agents.llm_agent import Agent
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv
import os

from backend.adk.tools.cfe import cfe_callback
from backend.schema.cfe import CFEOutput

load_dotenv()

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "../../../prompts/")
ENV = Environment(loader=FileSystemLoader(PROMPT_DIR))


async def get_cfe_agent():
    """
    Get the CFE (Counterfactual Explanation) agent that combines
    baseline and context-aware recommendations.
    """
    template = ENV.get_template("cfe_combination.jinja2")
    
    cfe_agent = Agent(
        model='gemini-2.5-flash',
        name='CFEAgent',
        description='Agent that combines baseline and context-aware recommendations with counterfactual explanations.',
        instruction=template.render(),
        output_schema=CFEOutput,
        before_model_callback=cfe_callback
    )
    return cfe_agent
