"""
Database package for CRS Chatbot.
Uses Firestore when credentials are configured; falls back to in-memory stores otherwise.
"""

from .session_store import SessionStore
from .firestore_store import FirestoreSessionStore
from .conversation_store import ConversationStore
from .memory_store import MemorySessionStore, MemoryConversationStore
from .hf_store import HFConversationStore
from .config import get_session_store, get_conversation_store

__all__ = [
    "SessionStore",
    "FirestoreSessionStore",
    "ConversationStore",
    "MemorySessionStore",
    "MemoryConversationStore",
    "HFConversationStore",
    "get_session_store",
    "get_conversation_store",
]
