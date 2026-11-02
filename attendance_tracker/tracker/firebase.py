"""Lazy Firestore client.

Set FIREBASE_KEY_PATH to the path of your service account JSON file.
If it is not set, Google Application Default Credentials are used.
"""
import os

import firebase_admin
from firebase_admin import credentials, firestore

_db = None


def db():
    global _db
    if _db is None:
        if not firebase_admin._apps:
            key_path = os.environ.get("FIREBASE_KEY_PATH")
            if key_path:
                cred = credentials.Certificate(key_path)
            else:
                cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred)
        _db = firestore.client()
    return _db
