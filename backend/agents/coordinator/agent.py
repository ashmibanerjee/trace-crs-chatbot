from google.adk.agents import SequentialAgent
from google.adk.agents.llm_agent import Agent
from .task_agents import *

cq_gen = get_cq_agent()
rec_baseline = get_rec_baseline()

coordinator = Agent(
    model='gemini-2.5-flash',
    name='root_agent',
    description='A helpful coordinator for a travel recommender system which acts as an intermediary between the chat interface and the agentic backend.',
    instruction='Given a user query, your task is to first provide the query to the clarifying question generator to obtain the clarifying questions. Also provide only the input query to the recommender agent. The final output MUST be a JSON combining the outputs of both the sub agents.',
)

root_agent = SequentialAgent(name="pipeline", sub_agents=[coordinator, cq_gen, rec_baseline])
