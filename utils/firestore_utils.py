import os
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import firestore
from google.oauth2 import service_account


def get_firestore_client() -> firestore.Client:
    """
    Initialize Firestore client with credentials from settings.

    Returns:
        Configured Firestore client
    """
    # Get project root - go up from backend/adk/tools/ to crs-chatbot/
    project_root = Path(__file__).parent.parent

    # Load .env file explicitly
    env_path = project_root / '.env'
    load_dotenv(env_path)

    print(f"[Callback] Loading .env from: {env_path}")
    print(f"[Callback] .env exists: {env_path.exists()}")

    # Get values from environment
    credentials_path = os.getenv('FIREBASE_GOOGLE_APPLICATION_CREDENTIALS')
    project_id = os.getenv('FIREBASE_PROJECT_ID')

    print(f"[Callback] Raw credentials path: {credentials_path}")
    print(f"[Callback] Firebase project ID: {project_id}")

    if not credentials_path:
        raise ValueError("FIREBASE_GOOGLE_APPLICATION_CREDENTIALS not set in .env file")

    if not project_id:
        raise ValueError("FIREBASE_PROJECT_ID not set in .env file")

    # Resolve to absolute path if relative
    if not os.path.isabs(credentials_path):
        credentials_path = str(project_root / credentials_path)

    # Verify file exists
    if not os.path.exists(credentials_path):
        raise FileNotFoundError(f"Credentials file not found: {credentials_path}")

    print(f"[Callback] Using credentials: {credentials_path}")
    print(f"[Callback] Using project: {project_id}")

    # Load credentials explicitly
    credentials = service_account.Credentials.from_service_account_file(credentials_path)

    # Initialize Firestore client with explicit credentials and project
    return firestore.Client(project=project_id, credentials=credentials)


async def ingest_response_firestore(collection_name, session_id, response) -> bool:
    try:
        db = get_firestore_client()
        doc_ref = db.collection(collection_name).document(session_id)
        doc_ref.set(response)  # This creates or replaces the document
        print(f"[Intent Response Ingestion] Successfully stored response for session {session_id}")
        return True
    except Exception as e:
        print(f"[Intent Response Ingestion] Error storing response for session {session_id}: {e}")
        return False
