"""
Database Configuration
Factory functions that fall back to in-memory stores when Firestore is not configured
or when credentials are invalid/expired.

The connection is probed eagerly so auth failures surface at startup rather than
mid-request (which would produce a cryptic gRPC traceback).
"""
import logging
import os
from pathlib import Path
from typing import Optional

from .session_store import SessionStore

logger = logging.getLogger(__name__)


def _resolve_credentials_path(credentials_path: Optional[str]) -> Optional[str]:
    if not credentials_path:
        return None
    if os.path.isabs(credentials_path):
        return credentials_path
    project_root = Path(__file__).parent.parent
    abs_path = str(project_root / credentials_path)
    print(f"[Config] Resolved credentials path: {abs_path}")
    print(f"[Config] Credentials file exists: {os.path.exists(abs_path)}")
    return abs_path


def _probe_firestore(db) -> bool:
    """
    Test credentials by refreshing the OAuth2 token directly (plain HTTPS, no gRPC).
    This fails in ~1 s instead of waiting for gRPC's 60 s retry timeout.
    Returns False on any auth or network error.
    """
    try:
        import google.auth.transport.requests
        request = google.auth.transport.requests.Request()
        creds = getattr(db, "_credentials", None)
        if creds is None:
            return True  # no credentials object — assume ADC / Cloud Run, let it through
        if hasattr(creds, "refresh"):
            creds.refresh(request)
        return True
    except Exception as exc:
        logger.warning("[Database] Firestore credential probe failed: %s", exc)
        return False


_session_store_instance = None
_conversation_store_instance = None


def get_session_store(backend: Optional[str] = None) -> SessionStore:
    global _session_store_instance
    if _session_store_instance is not None:
        return _session_store_instance

    from config import settings

    project_id = (settings.firebase_project_id or settings.google_cloud_project) if settings.use_firestore else None
    if not project_id:
        logger.warning("[Database] No Firestore project ID — using in-memory session store.")
        from .memory_store import MemorySessionStore
        _session_store_instance = MemorySessionStore()
        return _session_store_instance

    credentials_path = _resolve_credentials_path(settings.firebase_google_application_credentials)
    try:
        from .firestore_store import FirestoreSessionStore
        store = FirestoreSessionStore(
            project_id=project_id,
            credentials_path=credentials_path,
            collection_name="sessions",
        )
        if not _probe_firestore(store.db):
            raise RuntimeError("Firestore credential probe failed")
        _session_store_instance = store
    except Exception as e:
        logger.warning("[Database] Firestore unavailable (%s) — using in-memory session store.", e)
        from .memory_store import MemorySessionStore
        _session_store_instance = MemorySessionStore()

    return _session_store_instance


def get_conversation_store():
    """
    Priority order for conversation persistence:
      1. Firestore  — if FIREBASE_PROJECT_ID is set and credentials are valid
      2. HF Dataset — if HF_TOKEN + HF_DATASET_REPO are set
      3. In-memory  — fallback (data lost on restart, fine for demo)

    Returns the same singleton instance on every call so all callers share state.
    """
    global _conversation_store_instance
    if _conversation_store_instance is not None:
        return _conversation_store_instance

    from config import settings

    # --- 1. Firestore (only when explicitly opted in) ---
    project_id = (settings.firebase_project_id or settings.google_cloud_project) if settings.use_firestore else None
    if project_id:
        credentials_path = _resolve_credentials_path(settings.firebase_google_application_credentials)
        try:
            from .conversation_store import ConversationStore
            store = ConversationStore(
                project_id=project_id,
                credentials_path=credentials_path,
                collection_name="conversations",
            )
            if not _probe_firestore(store.db):
                raise RuntimeError("Firestore credential probe failed")
            logger.info("[Database] Using Firestore conversation store.")
            _conversation_store_instance = store
            return _conversation_store_instance
        except Exception as e:
            logger.warning("[Database] Firestore unavailable (%s), trying next option.", e)

    # --- 2. HF Dataset repo ---
    hf_token = os.getenv("HF_TOKEN") or settings.hf_token
    hf_repo = os.getenv("HF_DATASET_REPO") or settings.hf_dataset_repo
    if hf_token and hf_repo:
        try:
            from .hf_store import HFConversationStore
            _conversation_store_instance = HFConversationStore(repo_id=hf_repo, token=hf_token)
            logger.info("[Database] Using HF Dataset conversation store (%s).", hf_repo)
            return _conversation_store_instance
        except Exception as e:
            logger.warning("[Database] HF store unavailable (%s), falling back to in-memory.", e)

    # --- 3. In-memory ---
    logger.warning("[Database] No persistent store configured — using in-memory conversation store.")
    from .memory_store import MemoryConversationStore
    _conversation_store_instance = MemoryConversationStore()
    return _conversation_store_instance
