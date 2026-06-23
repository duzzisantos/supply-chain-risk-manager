import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import auth as firebase_auth, credentials

_firebase_initialized = False
security = HTTPBearer()


def _init_firebase():
    global _firebase_initialized
    if _firebase_initialized:
        return
    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "./firebase-service-account.json")
    if os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    else:
        firebase_admin.initialize_app()
    _firebase_initialized = True


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    _init_firebase()
    try:
        decoded = firebase_auth.verify_id_token(creds.credentials)
        return {
            "uid": decoded["uid"],
            "email": decoded.get("email"),
            "name": decoded.get("name"),
        }
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase token",
        )
