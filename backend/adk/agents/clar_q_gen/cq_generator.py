import asyncio
import json
import os
import sys
from typing import Dict, Any, List, Optional
# Define constants for paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.adk.assembly.run import _call_agent_async
from backend.adk.agents.clar_q_gen.agent import get_cq_agent
from backend.schema.schema import ClarifyingQuestion, CQOutput


def format_question(question_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform raw question data into the format expected by the frontend.

    Args:
        question_data: Raw question data from the agent

    Returns:
        Formatted question dictionary
    """
    return {
        'id': question_data['id'],
        'category': question_data['category'],
        'question': question_data['question'],
        'answer': None
    }

async def generate_clarifying_questions(query: str) -> CQOutput:
    """
    Generate clarifying questions for a user query.

    Args:
        query: The user's input query

    Returns:
        CQOutput instance with original query and list of formatted questions
    """
    cq_agent = await get_cq_agent()

    try:
        agent_name, response = await _call_agent_async(query, cq_agent)
        cq_data = json.loads(response)
        questions = [
            ClarifyingQuestion(**format_question(cq))
            for cq in cq_data.get('clarifying_questions', [])
        ]

        return CQOutput(
            query=cq_data.get('query', query),
            clarifying_questions=questions
        )
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error processing agent response: {e}")
        raise
    except Exception as e:
        print(f"Error calling agent: {e}")
        raise

if __name__ == "__main__":
    test_query = "Suggest places to visit in Europe in summer"
    result = asyncio.run(generate_clarifying_questions(test_query))
    print(json.dumps(result, indent=2))
