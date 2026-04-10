import hashlib
import os
import uuid

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from supabase import create_client, Client

router = APIRouter(tags=["keys"])

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")


def _supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def _hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


class CreateKeyRequest(BaseModel):
    user_id: str
    label: str = "Default Key"


@router.post("/create-key")
async def create_key(body: CreateKeyRequest, x_admin_secret: str = Header(None)):
    """
    Admin endpoint to create a NeuralGuard API key for a user.
    Protected by X-Admin-Secret header (set this to a long random string in .env).
    Returns the plaintext key ONCE — store it immediately.
    """
    admin_secret = os.environ.get("ADMIN_SECRET", "")
    if not admin_secret or x_admin_secret != admin_secret:
        raise HTTPException(403, "Forbidden")

    plaintext = f"ng-{uuid.uuid4().hex}"
    key_hash = _hash(plaintext)

    _supabase().table("api_keys").insert(
        {
            "user_id": body.user_id,
            "key_hash": key_hash,
            "label": body.label,
            "is_active": True,
        }
    ).execute()

    return {"key": plaintext, "message": "Copy this key — it will not be shown again."}


@router.post("/revoke-key/{key_id}")
async def revoke_key(key_id: str, x_admin_secret: str = Header(None)):
    admin_secret = os.environ.get("ADMIN_SECRET", "")
    if not admin_secret or x_admin_secret != admin_secret:
        raise HTTPException(403, "Forbidden")

    _supabase().table("api_keys").update(
        {"is_active": False, "revoked_at": "now()"}
    ).eq("id", key_id).execute()

    return {"status": "revoked"}
