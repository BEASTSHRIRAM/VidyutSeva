"""
Auth router — Phone + OTP authentication.
Generates a 6-digit OTP (simulated — logs to console / returns in dev mode).
Returns JWT tokens on verification.
"""

import os
import random
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)

# ── JWT helpers ────────────────────────────────────────────────────────────────

def _jwt_encode(payload: dict) -> str:
    try:
        import jwt
        secret = os.getenv("JWT_SECRET")
        return jwt.encode(payload, secret, algorithm="HS256")
    except ImportError:
        import base64, json as _json
        # Fallback: base64-encoded JSON (dev only, not secure)
        return base64.b64encode(_json.dumps(payload).encode()).decode()


def _jwt_decode(token: str) -> dict:
    try:
        import jwt
        secret = os.getenv("JWT_SECRET")
        return jwt.decode(token, secret, algorithms=["HS256"])
    except ImportError:
        import base64, json as _json
        return _json.loads(base64.b64decode(token.encode()).decode())
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Dependency: decode JWT and return user payload."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    return _jwt_decode(credentials.credentials)


def get_optional_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict | None:
    """Dependency: return user payload or None (for public endpoints)."""
    if not credentials:
        return None
    try:
        return _jwt_decode(credentials.credentials)
    except Exception:
        return None


# ── Pydantic models ────────────────────────────────────────────────────────────

class SendOTPRequest(BaseModel):
    phone_number: str


class VerifyOTPRequest(BaseModel):
    phone_number: str
    otp: str
    name: str | None = None


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/send-otp")
async def send_otp(body: SendOTPRequest):
    """
    Send OTP to phone number.
    In production: integrate with Twilio / Gupshup SMS.
    In dev: returns OTP in response (also logged to console).
    """
    from database.supabase_client import upsert_user_otp

    phone = body.phone_number.strip().replace(" ", "").replace("-", "")
    if not phone or len(phone) < 10:
        raise HTTPException(status_code=400, detail="Invalid phone number")

    otp = str(random.randint(100000, 999999))
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()

    upsert_user_otp(phone, otp, expires_at)

    # In production: send via SMS provider
    logger.info(f"[Auth] OTP for {phone}: {otp}")

    dev_mode = os.getenv("DEV_MODE", "true").lower() == "true"
    response = {"message": f"OTP sent to {phone}"}
    if dev_mode:
        response["otp"] = otp  # expose in dev mode only

    return response


@router.post("/verify-otp")
async def verify_otp(body: VerifyOTPRequest):
    """
    Verify OTP and return JWT token.
    Also auto-merges any anonymous complaints for this phone number.
    """
    from database.supabase_client import (
        get_user_by_phone,
        verify_user_otp,
        merge_anonymous_complaints,
    )

    phone = body.phone_number.strip().replace(" ", "").replace("-", "")
    user = get_user_by_phone(phone)

    if not user or not user.get("otp_code"):
        raise HTTPException(status_code=400, detail="No OTP found for this number. Request a new one.")

    otp_expires = user.get("otp_expires_at")
    if otp_expires:
        # Parse and check expiry
        from dateutil.parser import parse as parse_dt
        try:
            exp = parse_dt(str(otp_expires))
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > exp:
                raise HTTPException(status_code=400, detail="OTP expired. Request a new one.")
        except HTTPException:
            raise
        except Exception:
            pass  # date parsing failed, continue

    if user.get("otp_code") != body.otp.strip():
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # Mark verified, set name if provided
    updated = verify_user_otp(phone, body.name)
    user_id = str(updated.get("id", user.get("id")))

    # Auto-merge anonymous complaints
    try:
        merge_anonymous_complaints(phone, user_id)
    except Exception as e:
        logger.warning(f"[Auth] Complaint merge error: {e}")

    # Issue JWT
    role = updated.get("role", "citizen")
    payload = {
        "sub": user_id,
        "phone": phone,
        "name": updated.get("name") or body.name or "User",
        "role": role,
        "exp": int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp()),
    }
    token = _jwt_encode(payload)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "phone": phone,
            "name": payload["name"],
            "role": role,
        },
    }


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Return current user info from JWT."""
    return user
