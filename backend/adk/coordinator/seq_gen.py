import asyncio
from typing import Optional

import os
import sys
_file_dir = os.path.dirname(__file__)  # backend/agents/coordinator
_project_root = os.path.abspath(os.path.join(_file_dir, "..", ".."))  # project root that contains `backend`
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
from backend.adk.coordinator.run import call_agent_async
from backend.adk.agents.clar_q_gen.agent import get_cq_agent
from backend.adk.agents.intent_classification.agent import get_ic_agent
from google.adk.agents import SequentialAgent
import json

async def main(query: Optional[str] = None):
    cq_gen_root = await (get_cq_agent())
    agent_name, responses = asyncio.run(call_agent_async(query, cq_gen_root))
    cq_gen_response = json.loads(responses)
    print("here")

asyncio.run(main("Suggest places to visit in Europe in summer"))