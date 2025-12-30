from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
from typing import Optional
from google.genai import types
from google.adk.sessions import InMemorySessionService
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()

APP_NAME = "crs-chat_app"
USER_ID = "user_1"
SESSION_ID = "session_001"

# Session and Runner
async def setup_session_and_runner(root_agent: Agent = None, session_id: str = SESSION_ID):
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
async def call_agent_async(query: str, root_agent: Agent = None, session_id: str = SESSION_ID):
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
    session, runner = await setup_session_and_runner(root_agent=root_agent, session_id=session_id)
    events = runner.run_async(user_id=USER_ID, session_id=session_id, new_message=content)

    async for event in events:
        if event.is_final_response():
            final_response = event.content.parts[0].text
            return event.author, final_response


