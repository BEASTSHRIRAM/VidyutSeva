"""
Complaints router — citizen reports with upvote system and escalation trigger.
"""

import logging
import random
import string
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from routers.auth import get_current_user, get_optional_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/complaints", tags=["complaints"])


def _generate_complaint_id() -> str:
    now = datetime.now(timezone.utc)
    suffix = "".join(random.choices(string.digits, k=4))
    return f"VSEVA-{now.strftime('%y%m%d')}-{suffix}"


# ── Pydantic models ────────────────────────────────────────────────────────────

class ComplaintCreate(BaseModel):
    text: str
    area: str
    phone_number: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    source: str = "web"


class ComplaintUpdate(BaseModel):
    status: str | None = None
    fault_type: str | None = None


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("")
async def list_complaints(
    area: str | None = Query(None),
    status: str | None = Query(None),
    sort: str = Query("upvotes"),       # "upvotes" | "recent"
    limit: int = Query(50),
):
    """
    Public endpoint — list complaints sorted by upvotes (default) or recency.
    Used for the public community dashboard.
    """
    from database.supabase_client import get_complaints
    complaints = get_complaints(area=area, status=status, sort=sort, limit=limit)
    # Serialize datetimes
    return [
        {k: str(v) if hasattr(v, "isoformat") else v for k, v in c.items()}
        for c in complaints
    ]


@router.post("")
async def create_complaint(
    body: ComplaintCreate,
    user: dict | None = Depends(get_optional_user),
):
    """
    Submit a new complaint. Works for both authenticated and anonymous users.
    Authenticated users get user_id linked; anonymous tracked by phone.
    Triggers escalation pipeline if hardware fault.
    """
    from database.supabase_client import create_complaint as db_create
    from agents.escalation_agent import run_escalation_pipeline

    complaint_data = {
        "complaint_id": _generate_complaint_id(),
        "text": body.text.strip(),
        "area": body.area.strip(),
        "source": body.source,
        "phone_number": body.phone_number,
        "latitude": body.latitude,
        "longitude": body.longitude,
        "status": "new",
        "upvote_count": 0,
    }

    if user:
        complaint_data["user_id"] = user.get("sub")
        if not complaint_data["phone_number"]:
            complaint_data["phone_number"] = user.get("phone")

    saved = db_create(complaint_data)
    if not saved:
        raise HTTPException(status_code=500, detail="Failed to save complaint")

    # Fire-and-forget escalation pipeline
    import asyncio
    try:
        asyncio.create_task(run_escalation_pipeline(saved))
    except RuntimeError:
        # No running event loop in some contexts — run directly
        import threading
        threading.Thread(
            target=lambda: asyncio.run(run_escalation_pipeline(saved)),
            daemon=True,
        ).start()

    return {
        k: str(v) if hasattr(v, "isoformat") else v
        for k, v in saved.items()
    }


@router.post("/{complaint_id}/upvote")
async def upvote_complaint(
    complaint_id: str,
    user: dict = Depends(get_current_user),
):
    """
    Toggle upvote on a complaint. Requires authentication.
    Returns updated upvote count and whether user has upvoted.
    """
    from database.supabase_client import toggle_upvote
    user_id = user.get("sub")
    result = toggle_upvote(complaint_id, user_id)
    return result


@router.get("/{complaint_id}")
async def get_complaint(complaint_id: str):
    """Get a single complaint by complaint_id (e.g. VSEVA-260416-7843) or UUID."""
    from database.supabase_client import get_complaint_by_id
    row = get_complaint_by_id(complaint_id)
    if not row:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return {k: str(v) if hasattr(v, "isoformat") else v for k, v in row.items()}


@router.patch("/{complaint_id}")
async def update_complaint(
    complaint_id: str,
    body: ComplaintUpdate,
    user: dict = Depends(get_current_user),
):
    """Admin: update status or fault_type of a complaint."""
    if user.get("role") not in ("admin",):
        raise HTTPException(status_code=403, detail="Admin only")
    from database.supabase_client import update_complaint as db_update
    data = {k: v for k, v in body.dict().items() if v is not None}
    updated = db_update(complaint_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return {k: str(v) if hasattr(v, "isoformat") else v for k, v in updated.items()}


@router.get("/admin/escalations")
async def list_escalations(
    user: dict = Depends(get_current_user),
    limit: int = Query(50),
):
    """BESCOM Admin: get all escalations sorted by most recent."""
    if user.get("role") not in ("admin",):
        raise HTTPException(status_code=403, detail="Admin only")
    from database.supabase_client import get_escalations
    escalations = get_escalations(limit=limit)
    return [
        {k: str(v) if hasattr(v, "isoformat") else v for k, v in e.items()}
        for e in escalations
    ]
