# Naming this file "task_agents" because running adk requires the root_agent (or coordinator) to be stored in agent.py 
# TODO (AS): convert to classes with base class and inherited agent classes 

from google.adk.agents.llm_agent import Agent
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv

load_dotenv()

PROMPT_DIR = "../prompts/"
ENV = Environment(loader=FileSystemLoader(PROMPT_DIR))

def get_cq_agent():
    cq_template = ENV.get_template("clarifying_questions.jinja2")

    clarifyingQuestionGenerator = Agent(
        model='gemini-2.5-flash',
        name='clarifying_question_generator',
        description='An agent that generates clarifying questions, given an user query.',
        instruction=cq_template.render(),
        # instruction=template,
    )
    return clarifyingQuestionGenerator

def get_rec_baseline():
    rec_template = ENV.get_template("rec_baseline.jinja2")

    recommenderBaseline = Agent(
        model='gemini-2.5-flash',
        name='recommender_baseline',
        description='An agent that generates travel recommendations for city trips, given an user query.',
        instruction=rec_template.render(),
        # instruction=template,
    )
    return recommenderBaseline