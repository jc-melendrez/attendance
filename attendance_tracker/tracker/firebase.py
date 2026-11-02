"""Lazy Firestore client.

Set FIREBASE_KEY_PATH to the path of your service account JSON file.
If it is not set, Google Application Default Credentials are used.
"""
import json
import os

import firebase_admin
from firebase_admin import credentials, firestore

_db = None


def _load_cred(key_path):
    if os.path.exists(key_path):
        with open(key_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = key_path

    try:
        data = json.loads(content, strict=False)
        return credentials.Certificate(data)
    except Exception:
        return credentials.Certificate(key_path)


def db():
    global _db
    if _db is None:
        if not firebase_admin._apps:
            key_path = os.environ.get("FIREBASE_KEY_PATH")
            if key_path:
                cred = _load_cred(key_path)
            else:
                cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred)
        _db = firestore.client()
    return _db
