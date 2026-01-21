from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
from typing import Optional, Dict, Union, List
from google.genai import types
from google.adk.sessions import InMemorySessionService
import asyncio
from dotenv import load_dotenv
import os
import json
from backend.schema.cfe import (
    CFEOutput
)
from backend.schema.recSys import RecsysOutput
from backend.schema.intentClassifier import IntentClassificationOutput

load_dotenv()

APP_NAME = "crs-chat_app"
USER_ID = "user_1"
SESSION_ID = "session_001"


# Session and Runner
async def _setup_session_and_runner(root_agent: Agent = None, session_id: str = SESSION_ID):
    """
    Setup ADK session and runner
    
    Args:
        root_agent: The agent to run
        session_id: Session identifier (defaults to SESSION_ID constant)
    """
    session_service = InMemorySessionService()
    session = await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=session_id)
    runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)
    return session, runner


# Agent Interaction
async def _call_agent_async(query: str, root_agent: Agent = None, session_id: str = SESSION_ID):
    """
    Call agent asynchronously with query
    
    Args:
        query: User query text (can contain embedded session_id as [SESSION_ID:xxx])
        root_agent: The agent to invoke
        session_id: Session identifier for ADK runner
        
    Returns:
        Tuple of (agent_name, response_text)
    """
    content = types.Content(role='user', parts=[types.Part(text=query)])
    session, runner = await _setup_session_and_runner(root_agent=root_agent, session_id=session_id)
    events = runner.run_async(user_id=USER_ID, session_id=session_id, new_message=content)

    async for event in events:
        if event.is_final_response():
            final_response = event.content.parts[0].text
            yield event.author, final_response


async def get_model_response(
        query: str,
        root_agent: Agent,
        session_id: Optional[str] = SESSION_ID,
        return_cfe_only: bool = False
) -> Union[List[Dict], Dict, CFEOutput]:
    """
    Get model response from agent pipeline.

    Args:
        query: User query text
        root_agent: The agent to invoke
        session_id: Session identifier
        return_cfe_only: If True, returns only the CFE agent response as a parsed CFEOutput object

    Returns:
        If return_cfe_only is True: CFEOutput object
        Otherwise: List of response dictionaries with agent_name and response_text
    """
    responses = []
    async for agent_name, response_text in _call_agent_async(query, root_agent, session_id):
        response_dict = {
            "agent_name": agent_name,
            "response_text": response_text
        }
        responses.append(response_dict)

    if return_cfe_only:
        # Filter for CFE agent response
        cfe_responses = [r for r in responses if r["agent_name"] == "CFEAgent"]
        if cfe_responses:
            # Parse and return as CFEOutput object
            response_data = json.loads(cfe_responses[0]["response_text"])
            return CFEOutput(**response_data)
        return None

    return responses


async def get_parsed_responses(
        query: str,
        root_agent: Agent,
        session_id: Optional[str] = SESSION_ID
) -> Dict[str, Union[IntentClassificationOutput, RecsysOutput, CFEOutput]]:
    """
    Get all agent responses parsed into their respective Pydantic models.

    Returns:
        Dictionary with agent names as keys and parsed Pydantic models as values
    """
    responses = await get_model_response(query, root_agent, session_id)
    parsed_responses = {}

    for response in responses:
        agent_name = response["agent_name"]
        response_data = json.loads(response["response_text"])

        if agent_name == "intent_classification":
            parsed_responses[agent_name] = IntentClassificationOutput(**response_data)
        elif agent_name == "recsys":
            parsed_responses[agent_name] = RecsysOutput(**response_data)
        elif agent_name == "CFEAgent":
            parsed_responses[agent_name] = CFEOutput(**response_data)

    return parsed_responses
