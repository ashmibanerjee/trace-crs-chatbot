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

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "../../../prompts/")
ENV = Environment(loader=FileSystemLoader(PROMPT_DIR))


cq_agent = get_cq_agent()
ic_agent = get_ic_agent()
rec_baseline_agent = get_recsys_agent(has_context=False)
ca_recsys_agent = get_recsys_agent(has_context=True)
cfe_agent = get_cfe_agent()


sequential_pipeline = SequentialAgent(
    name="SequentialPipeline",
     sub_agents=[cq_agent, ic_agent, ca_recsys_agent],
     description="Runs the sequential pipeline of CQ + IC + recommender"
)
parallel_agents = ParallelAgent(
     name="ParallelRecAgents",
     sub_agents=[sequential_pipeline, rec_baseline_agent],
     description="Runs multiple agents in parallel to gather information."
 )

# Create the MergerAgent (Combines outputs from parallel agents) using CFE agent
overall_workflow = SequentialAgent(
     name="CRSPipeline",
     # Run parallel first, then merge with CFE
     sub_agents=[parallel_agents, cfe_agent],
     description="Coordinates parallel research and synthesizes the results with counterfactual explanations."
 )
root_agent = overall_workflow
