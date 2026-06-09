"""
HuggingFace Dataset repository conversation store.

Each session is stored as an individual JSON file at:
  {repo_id}/data/{session_id}.json

Pushes are fire-and-forget (non-blocking): a background thread handles the upload
so the chat response is never delayed by a slow network write.

Required env vars (set as HF Space secrets or in .env):
  HF_TOKEN          — HF token with write access to the dataset repo
  HF_DATASET_REPO   — e.g. "your-username/crs-conversations" (private is fine)
"""
import json
import logging
import os
import threading
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Module-level in-memory cache so get_conversation() works without a network round-trip
_cache: Dict[str, Dict[str, Any]] = {}


def _upload(repo_id: str, token: str, session_id: str, data: dict) -> None:
    """Blocking upload — always called from a daemon thread."""
    try:
        from huggingface_hub import HfApi
        api = HfApi(token=token)
        content = json.dumps(data, indent=2, ensure_ascii=False).encode()
        api.upload_file(
            path_or_fileobj=content,
            path_in_repo=f"data/{session_id}.json",
            repo_id=repo_id,
            repo_type="dataset",
            commit_message=f"session {session_id}",
        )
        logger.info("[HFStore] Uploaded %s to %s", session_id, repo_id)
    except Exception as exc:
        logger.warning("[HFStore] Upload failed for %s: %s", session_id, exc)


def _push_async(repo_id: str, token: str, session_id: str, data: dict) -> None:
    """Fire-and-forget: upload in a daemon thread so the chat is never blocked."""
    t = threading.Thread(target=_upload, args=(repo_id, token, session_id, data), daemon=True)
    t.start()


class HFConversationStore:
    """
    Stores conversations as JSON files in a HuggingFace Dataset repository.
    Reads are served from an in-process cache (no network cost on get).
    Writes are async (background thread) so they never delay the response.
    """

    def __init__(self, repo_id: str, token: str):
        self._repo_id = repo_id
        self._token = token

    def _record(self, session_id: str, data: dict) -> dict:
        now = datetime.now().isoformat()
        return {**data, "session_id": session_id, "updated_at": now}

    async def create_conversation(self, session_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        record = self._record(session_id, {**data, "created_at": datetime.now().isoformat()})
        _cache[session_id] = record
        _push_async(self._repo_id, self._token, session_id, record)
        return record

    async def get_conversation(self, session_id: str) -> Optional[Dict[str, Any]]:
        return _cache.get(session_id)

    async def update_conversation(self, session_id: str, updates: Dict[str, Any]) -> bool:
        existing = _cache.get(session_id, {"session_id": session_id})
        existing.update(updates)
        existing["updated_at"] = datetime.now().isoformat()
        _cache[session_id] = existing
        _push_async(self._repo_id, self._token, session_id, existing)
        return True
