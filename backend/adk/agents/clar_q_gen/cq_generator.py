import asyncio
import json
import os
import sys
from typing import Dict, Any, List, Optional

# Define constants for paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.adk.coordinator.run import call_agent_async
from backend.adk.agents.clar_q_gen.agent import get_cq_agent
from backend.adk.agents.intent_classification.agent import get_ic_agent
from google.adk.agents import SequentialAgent


def format_question(question_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform raw question data into the format expected by the frontend.

    Args:
        question_data: Raw question data from the agent

    Returns:
        Formatted question dictionary
    """
    return {
        'id': question_data['q_id'],
        'category': question_data['q_category'],
        'question': question_data['clarify_q'],
        'answer': None
    }

async def generate_clarifying_questions(query: str) -> Dict[str, Any]:
    """
    Generate clarifying questions for a user query.

    Args:
        query: The user's input query

    Returns:
        Dictionary with original query and list of formatted questions,
        or empty dict if generation fails
    """
    cq_agent = await get_cq_agent()

    try:
        agent_name, response = await call_agent_async(query, cq_agent)
        cq_data = json.loads(response)
        questions = [
            format_question(cq)
            for cq in cq_data.get('clarifying_questions', [])
        ]

        return {
            'original_query': cq_data.get('query', query),
            'questions': questions
        }
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error processing agent response: {e}")
        return {}
    except Exception as e:
        print(f"Error calling agent: {e}")
        return {}

if __name__ == "__main__":
    test_query = "Suggest places to visit in Europe in summer"
    result = asyncio.run(generate_clarifying_questions(test_query))
    print(json.dumps(result, indent=2))
