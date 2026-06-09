"""
In-memory fallback stores used when Firestore credentials are not configured.
Data lives only for the lifetime of the process — suitable for demo/conference use.
"""
from typing import Any, Dict, Optional
from datetime import datetime

from .session_store import SessionStore

# Module-level dicts shared across all store instances (process-scoped)
_sessions: Dict[str, Dict[str, Any]] = {}
_conversations: Dict[str, Dict[str, Any]] = {}


class MemorySessionStore(SessionStore):
    async def create_session(self, session_id: str, session_data: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.now().isoformat()
        record = {**session_data, "id": session_id, "created_at": now, "last_activity": now}
        _sessions[session_id] = record
        return record

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return _sessions.get(session_id)

    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        existing = _sessions.get(session_id, {})
        existing.update(updates)
        existing["last_activity"] = datetime.now().isoformat()
        _sessions[session_id] = existing
        return True

    async def delete_session(self, session_id: str) -> bool:
        _sessions.pop(session_id, None)
        return True


class MemoryConversationStore:
    async def create_conversation(self, session_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.now().isoformat()
        record = {**data, "session_id": session_id, "created_at": now, "updated_at": now}
        _conversations[session_id] = record
        return record

    async def get_conversation(self, session_id: str) -> Optional[Dict[str, Any]]:
        return _conversations.get(session_id)

    async def update_conversation(self, session_id: str, updates: Dict[str, Any]) -> bool:
        existing = _conversations.get(session_id, {"session_id": session_id})
        existing.update(updates)
        existing["updated_at"] = datetime.now().isoformat()
        _conversations[session_id] = existing
        return True
