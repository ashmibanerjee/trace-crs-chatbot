from google.adk.agents.llm_agent import Agent
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv

load_dotenv()

PROMPT_DIR = "../../prompts/"
ENV = Environment(loader=FileSystemLoader(PROMPT_DIR))

cq_template = ENV.get_template("clarifying_questions.jinja2")

clarifyingQuestionGenerator = Agent(
    model='gemini-2.5-flash',
    name='clarifying_question_generator',
    description='An agent that generates clarifying questions, given an user query.',
    instruction=cq_template.render(),
    # instruction=template,
)

root_agent = clarifyingQuestionGenerator # ONLY FOR TESTING PURPOSES