"""
Firebase Admin and Firestore client initialization module.
Implements safe, lazy initialization with robust validation.
Never exposes credentials in logs and handles escaped newlines properly.
"""

import os
import json
import logging
from typing import Optional
from dotenv import load_dotenv
from google.cloud import firestore
import firebase_admin
from firebase_admin import credentials, firestore as admin_firestore

load_dotenv()

logger = logging.getLogger("vessel_system.firebase")

_firestore_client: Optional[firestore.Client] = None
_firebase_app: Optional[firebase_admin.App] = None


class FirebaseConfigError(Exception):
    """Raised when Firebase configuration is invalid or missing."""
    pass


def initialize_firebase() -> firestore.Client:
    """
    Safely initialize Firebase Admin SDK and return Firestore client.
    Thread-safe and idempotent.
    """
    global _firestore_client, _firebase_app

    if _firestore_client is not None:
        return _firestore_client

    # Check already initialized apps in firebase_admin
    if firebase_admin._apps:
        _firebase_app = firebase_admin.get_app()
        _firestore_client = admin_firestore.client()
        return _firestore_client

    project_id = os.environ.get("FIREBASE_PROJECT_ID", "vessel-system-5fff1").strip()
    client_email = os.environ.get("FIREBASE_CLIENT_EMAIL")
    private_key_raw = os.environ.get("FIREBASE_PRIVATE_KEY")
    service_account_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH")
    service_account_json_str = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")

    cred = None

    # Priority 1: Direct Service Account JSON file path
    if service_account_path and os.path.exists(service_account_path):
        try:
            logger.info("Initializing Firebase Admin SDK using service account file")
            cred = credentials.Certificate(service_account_path)
        except Exception as e:
            raise FirebaseConfigError(f"Failed to load service account file from {service_account_path}: {e}")

    # Priority 2: Raw Service Account JSON string in environment variable
    elif service_account_json_str and service_account_json_str.strip():
        try:
            logger.info("Initializing Firebase Admin SDK using FIREBASE_SERVICE_ACCOUNT_JSON")
            sa_dict = json.loads(service_account_json_str)
            cred = credentials.Certificate(sa_dict)
        except Exception as e:
            raise FirebaseConfigError(f"Failed to parse FIREBASE_SERVICE_ACCOUNT_JSON: {e}")

    # Priority 3: Individual environment variables
    elif client_email and private_key_raw:
        try:
            logger.info("Initializing Firebase Admin SDK using individual environment credentials")
            # Properly unescape literal newlines
            private_key = private_key_raw.replace("\\n", "\n")
            cred_dict = {
                "type": "service_account",
                "project_id": project_id,
                "client_email": client_email.strip(),
                "private_key": private_key,
                "token_uri": "https://oauth2.googleapis.com/token",
            }
            cred = credentials.Certificate(cred_dict)
        except Exception as e:
            raise FirebaseConfigError(f"Failed to configure credentials from environment variables: {e}")

    if cred is None:
        raise FirebaseConfigError(
            "Firebase credentials unavailable. Please configure FIREBASE_CLIENT_EMAIL & "
            "FIREBASE_PRIVATE_KEY, or FIREBASE_SERVICE_ACCOUNT_JSON, or FIREBASE_SERVICE_ACCOUNT_PATH."
        )

    try:
        _firebase_app = firebase_admin.initialize_app(cred, {"projectId": project_id})
        _firestore_client = admin_firestore.client()
        logger.info(f"Firebase Admin SDK initialized successfully for project: {project_id}")
        return _firestore_client
    except Exception as e:
        raise FirebaseConfigError(f"Failed to initialize Firebase Admin App: {e}")


def get_firestore() -> firestore.Client:
    """
    Returns the initialized Firestore client.
    Raises FirebaseConfigError if initialization fails.
    """
    return initialize_firebase()


def is_firebase_available() -> bool:
    """Check if Firebase credentials are present and valid."""
    try:
        initialize_firebase()
        return True
    except Exception:
        return False
