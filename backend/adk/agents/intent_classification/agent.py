import os
from pathlib import Path
from google.adk.agents.llm_agent import Agent
from jinja2 import Environment, FileSystemLoader
from backend.adk.tools.intent_classifier import check_clarification_status_callback
from backend.schema.schema import IntentClassificationOutput
from dotenv import load_dotenv

load_dotenv()


# Setup Jinja2 environment - point to prompts directory
# Path is: agents/intent_classification -> agents -> adk -> backend -> prompts
prompts_dir = Path(__file__).parent.parent.parent.parent / 'prompts'
file_loader = FileSystemLoader(str(prompts_dir))
env = Environment(loader=file_loader)
cq_template = env.get_template('intent_classification.jinja2')


async def get_ic_agent():
    """
    Initialize and return the Intent Classification agent with callback

    Returns:
        Configured Agent instance with before_model_callback
    """
    intentClassifierAgent = Agent(
        model='gemini-2.5-flash',
        name='intent_classification',
        description='An agent that generates user travel intents from the user query + clarifying questions.',
        instruction=cq_template.render(),
        output_schema=IntentClassificationOutput,
        before_model_callback=check_clarification_status_callback
    )

    print(f"[Agent Init] Intent Classifier initialized")
    print(f"[Agent Init] Callback attached: {intentClassifierAgent.before_model_callback is not None}")

    return intentClassifierAgent