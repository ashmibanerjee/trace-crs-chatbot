"""
Firebase Admin SDK Initialization
Centralized Firebase initialization for both local and cloud environments
"""
import os
import logging
from typing import Optional

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_ADMIN_AVAILABLE = True
except ImportError:
    FIREBASE_ADMIN_AVAILABLE = False
    logging.warning("Firebase Admin SDK not installed. Run: pip install firebase-admin")

_firebase_app = None
_firestore_client = None


def initialize_firebase(
    project_id: str,
    credentials_path: Optional[str] = None
) -> firestore.client:
    """
    Initialize Firebase Admin SDK with automatic credential detection

    Args:
        project_id: Firebase project ID (required)
        credentials_path: Path to service account JSON (for local dev, optional)

    Returns:
        Firestore client instance
    """
    global _firebase_app, _firestore_client

    if not FIREBASE_ADMIN_AVAILABLE:
        raise ImportError(
            "Firebase Admin SDK not installed. "
            "Install with: pip install firebase-admin"
        )

    # Check if Firebase Admin is already initialized
    try:
        _firebase_app = firebase_admin.get_app()
        if _firestore_client is None:
            _firestore_client = firestore.client()
        logging.info(f"[Firebase] Using existing Firebase app")
        return _firestore_client
    except ValueError:
        # Not initialized yet, proceed with initialization
        pass

    # Check if running in Google Cloud environment
    is_cloud_environment = (
        os.getenv('K_SERVICE') or  # Cloud Run
        os.getenv('GAE_ENV') or    # App Engine
        os.getenv('FUNCTION_NAME')  # Cloud Functions
    )

    try:
        if is_cloud_environment:
            # Use Application Default Credentials in Cloud
            logging.info(f"[Firebase] Running in GCP environment, using Application Default Credentials")
            cred = credentials.ApplicationDefault()
            _firebase_app = firebase_admin.initialize_app(cred, {
                'projectId': project_id,
            })
        elif credentials_path and os.path.exists(credentials_path):
            # Use JSON credentials file for local development
            logging.info(f"[Firebase] Using JSON credentials from: {credentials_path}")
            cred = credentials.Certificate(credentials_path)
            _firebase_app = firebase_admin.initialize_app(cred, {
                'projectId': project_id,
            })
        else:
            # Try Application Default Credentials as fallback
            logging.info(f"[Firebase] No credentials file found, trying Application Default Credentials")
            logging.info(f"[Firebase] Credentials path was: {credentials_path}")
            cred = credentials.ApplicationDefault()
            _firebase_app = firebase_admin.initialize_app(cred, {
                'projectId': project_id,
            })

        # Get Firestore client
        _firestore_client = firestore.client()
        logging.info(f"[Firebase] Initialized successfully (project: {project_id})")

        return _firestore_client

    except Exception as e:
        logging.error(
            f"[Firebase] Failed to initialize: {e}\n"
            f"Please either:\n"
            f"  1. Set FIREBASE_GOOGLE_APPLICATION_CREDENTIALS in .env\n"
            f"  2. Run: gcloud auth application-default login"
        )
        raise


def get_firestore_client() -> firestore.client:
    """
    Get the Firestore client instance

    Returns:
        Firestore client

    Raises:
        RuntimeError if Firebase hasn't been initialized
    """
    if not _firestore_client:
        raise RuntimeError(
            "Firebase not initialized. Call initialize_firebase() first."
        )
    return _firestore_client

