# Firebase + Firestore connection — JSON file ki jagah ye use karenge
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

_db = None

def init_firebase():
    global _db
    if _db is not None:
        return _db

    # Environment variable se service account load karo (Heroku/Render/Cloud Run safe)
    sa_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
    if sa_json:
        cred = credentials.Certificate(json.loads(sa_json))
    else:
        # Local development ke liye file se
        cred = credentials.Certificate("serviceAccountKey.json")

    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)

    _db = firestore.client()
    return _db

def get_db():
    return init_firebase()
