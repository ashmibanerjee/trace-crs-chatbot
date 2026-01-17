import os
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import firestore
from google.oauth2 import service_account


def get_firestore_client() -> firestore.Client:
    """
    Initialize Firestore client with credentials from settings.
    Supports both explicit service account files and Application Default Credentials (ADC).

    Priority:
    1. GOOGLE_APPLICATION_CREDENTIALS (standard GCP env var)
    2. FIREBASE_GOOGLE_APPLICATION_CREDENTIALS (legacy)
    3. Application Default Credentials (Cloud Run, GCE, etc.)

    Returns:
        Configured Firestore client
    """
    # Get project root - go up from utils/ to crs-chatbot/
    project_root = Path(__file__).parent.parent

    # Load .env file explicitly (for local development)
    env_path = project_root / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"[Firestore] Loaded .env from: {env_path}")
    else:
        print(f"[Firestore] No .env file found at: {env_path}, using environment variables")

    # Get values from environment
    # Check standard GCP env var first, then fall back to Firebase-specific one
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS') or \
                       os.getenv('FIREBASE_GOOGLE_APPLICATION_CREDENTIALS')
    project_id = os.getenv('FIREBASE_PROJECT_ID') or \
                 os.getenv('GOOGLE_CLOUD_PROJECT') or \
                 os.getenv('GCP_PROJECT')

    print(f"[Firestore] Credentials path: {credentials_path}")
    print(f"[Firestore] Project ID: {project_id}")

    # If no project ID, try to get it from credentials file or fail
    if not project_id:
        if credentials_path and os.path.exists(credentials_path):
            # Try to extract project_id from credentials file
            import json
            try:
                with open(credentials_path) as f:
                    creds_data = json.load(f)
                    project_id = creds_data.get('project_id')
                    print(f"[Firestore] Extracted project_id from credentials: {project_id}")
            except Exception as e:
                print(f"[Firestore] Could not extract project_id from credentials: {e}")

        if not project_id:
            raise ValueError(
                "Project ID not found. Set one of: "
                "FIREBASE_PROJECT_ID, GOOGLE_CLOUD_PROJECT, or GCP_PROJECT"
            )

    # Initialize client based on available credentials
    if credentials_path and credentials_path.strip():
        # Resolve to absolute path if relative
        if not os.path.isabs(credentials_path):
            credentials_path = str(project_root / credentials_path)

        # Verify file exists
        if not os.path.exists(credentials_path):
            print(f"[Firestore] WARNING: Credentials file not found: {credentials_path}")
            print(f"[Firestore] Falling back to Application Default Credentials")
            return firestore.Client(project=project_id)

        print(f"[Firestore] Using explicit credentials: {credentials_path}")

        # Load credentials explicitly
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        return firestore.Client(project=project_id, credentials=credentials)
    else:
        # Use Application Default Credentials (ADC)
        # This works on Cloud Run, GCE, GKE, or local with `gcloud auth application-default login`
        print(f"[Firestore] Using Application Default Credentials for project: {project_id}")
        return firestore.Client(project=project_id)


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
