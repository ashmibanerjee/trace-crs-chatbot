import asyncio

from google.adk.agents import ParallelAgent, LlmAgent, SequentialAgent
import os
import sys
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv
from backend.adk.agents.intent_classification.agent import get_ic_agent
from backend.adk.agents.recsys.agent import get_recsys_agent
from backend.adk.agents.clar_q_gen.agent import get_cq_agent
from backend.adk.agents.cfe.agent import get_cfe_agent
from backend.schema.schema import CFEOutput

load_dotenv()

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "../../prompts/")
ENV = Environment(loader=FileSystemLoader(PROMPT_DIR))


async def create_pipeline():
    """Initialize and return the root agent pipeline."""
    ic_agent, rec_baseline_agent, ca_recsys_agent = await asyncio.gather(
        get_ic_agent(),
        get_recsys_agent(has_context=False),
        get_recsys_agent(has_context=True)
    )

    sequential_pipeline = SequentialAgent(
        name="SequentialPipeline",
        sub_agents=[ic_agent, ca_recsys_agent],
        description="Runs the sequential pipeline of CQ + IC + recommender"
    )

    parallel_agents = ParallelAgent(
        name="ParallelRecAgents",
        sub_agents=[sequential_pipeline, rec_baseline_agent],
        description="Runs multiple agents in parallel to gather information."
    )

    merger_agent = LlmAgent(
        name="CFEAgent",
        model='gemini-2.5-flash',
        instruction=ENV.get_template("cfe_combination.jinja2").render(),
        description="This is the CFE agent combining the outputs of multiple agents.",
        output_schema=CFEOutput
    )

    overall_workflow = SequentialAgent(
        name="CRSPipeline",
        sub_agents=[parallel_agents, merger_agent],
        description="Coordinates parallel research and synthesizes the results."
    )

    return overall_workflow


async def get_root_agent():
    """Async wrapper to get the root agent."""
    return await create_pipeline()
