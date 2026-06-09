"""
Async HuggingFace Inference API runner for structured output.
Runs the synchronous InferenceClient in a thread pool to avoid blocking the event loop.
"""
import asyncio
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="hf-runner")


def _get_client():
    import os
    from huggingface_hub import InferenceClient
    # Token read from environment — never accept it as a function argument
    token = os.getenv("HF_TOKEN")
    return InferenceClient(token=token)


def _extract_json(text: str) -> str:
    """Strip markdown fences and return the outermost JSON object."""
    # Remove ```json ... ``` or ``` ... ``` fences
    text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end >= start:
        return text[start : end + 1]
    return text


def _call_hf_sync(system_prompt: str, user_message: str, model: str, max_tokens: int) -> str:
    """Blocking HF chat_completion — called from a thread."""
    client = _get_client()
    response = client.chat_completion(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


async def call_structured(
    system_prompt: str,
    user_message: str,
    schema: Type[BaseModel],
    model: Optional[str] = None,
    max_tokens: int = 3000,
) -> Dict[str, Any]:
    """
    Call HF Inference API asynchronously and return a dict conforming to *schema*.
    Retries once with an explicit reminder if the first attempt produces invalid JSON.
    """
    from config import settings

    resolved_model = model or settings.hf_gemma_model
    schema_str = json.dumps(schema.model_json_schema(), indent=2)
    json_footer = (
        "\n\n---\n"
        "CRITICAL INSTRUCTION: your entire response MUST be a single raw JSON object. "
        "Start with { and end with }. No prose, no markdown fences, no extra text.\n"
        f"Follow this JSON schema exactly:\n{schema_str}"
    )

    loop = asyncio.get_event_loop()
    last_error: Exception = RuntimeError("unknown")

    for attempt in range(2):
        extra = "" if attempt == 0 else "\n\nRemember: output ONLY the JSON object, nothing else."
        full_system = system_prompt + json_footer + extra
        try:
            raw = await loop.run_in_executor(
                _executor,
                _call_hf_sync,
                full_system,
                user_message,
                resolved_model,
                max_tokens,
            )
            logger.debug("[HF] Raw response (attempt %d): %.300s", attempt + 1, raw)
            return json.loads(_extract_json(raw))
        except json.JSONDecodeError as exc:
            logger.warning("[HF] JSON parse failed (attempt %d): %s", attempt + 1, exc)
            last_error = exc

    raise RuntimeError(
        f"HF model did not return valid JSON after 2 attempts. Last error: {last_error}"
    )
