from google.adk.agents.llm_agent import Agent
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv

load_dotenv()

PROMPT_DIR = "../../prompts/"
ENV = Environment(loader=FileSystemLoader(PROMPT_DIR))

rec_template = ENV.get_template("rec_baseline.jinja2")

recommenderBaseline = Agent(
    model='gemini-2.5-flash',
    name='recommender_baseline',
    description='An agent that generates travel recommendations for city trips, given an user query.',
    instruction=rec_template.render(),
    # instruction=template,
)

root_agent = recommenderBaseline # ONLY FOR TESTING PURPOSES
