from google.adk.agents import ParallelAgent, LlmAgent, SequentialAgent
import os
import sys

from backend.adk.agents.intent_classification.agent import get_ic_agent

_file_dir = os.path.dirname(__file__)  # backend/agents/coordinator
_project_root = os.path.abspath(os.path.join(_file_dir, "..", ".."))  # project root that contains `backend`
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
from backend.adk.agents.recsys.agent import get_rec_baseline
from backend.adk.agents.clar_q_gen.agent import get_cq_agent

cq_agent = get_cq_agent()
ic_agent = get_ic_agent()
rec_baseline_agent = get_rec_baseline()


sequential_pipeline = SequentialAgent(
    name="SequentialPipeline",
     sub_agents=[cq_agent, ic_agent],
     description="Runs the sequential pipeline of CQ + IC"
)
parallel_agents = ParallelAgent(
     name="ParallelRecAgents",
     sub_agents=[sequential_pipeline, rec_baseline_agent],
     description="Runs multiple research agents in parallel to gather information."
 )

# Create the MergerAgent (Combines outputs from parallel agents) TODO: CFE ---
merger_agent = LlmAgent(
    name="SynthesisAgent",
    model='gemini-2.5-flash',  # Or potentially a more powerful model if needed for synthesis
    instruction="# This is the CFE agent combining the outputs of multiple agents.\n",
    description="",
    output_schema=None  # Define an appropriate output schema if needed
)

# Create the SequentialAgent (Orchestrates the overall flow) ---
 # This is the main agent that will be run. It first executes the ParallelAgent
 # to populate the state, and then executes the MergerAgent to produce the final output.

final_sequential_pipeline_agent = SequentialAgent(
     name="CRSPipeline",
     # Run parallel first, then merge
     sub_agents=[parallel_agents, merger_agent],
     description="Coordinates parallel research and synthesizes the results."
 )
root_agent = final_sequential_pipeline_agent
