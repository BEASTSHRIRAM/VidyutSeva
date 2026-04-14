"""
Alert subscription routes.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database.supabase_client import (
    create_subscription,
    get_all_subscriptions,
    get_subscriptions_for_area,
)

router = APIRouter(prefix="/alerts", tags=["alerts"])


class SubscriptionCreate(BaseModel):
    area_name: str
    contact_method: str  # 'email', 'sms', 'whatsapp'
    contact_value: str   # email address or phone number


@router.post("/subscribe")
async def subscribe(sub: SubscriptionCreate):
    """Subscribe to proactive alerts for an area."""
    data = sub.model_dump()
    record = create_subscription(data)
    if not record:
        raise HTTPException(status_code=500, detail="Failed to create subscription")
    return record


@router.get("/subscriptions")
async def list_subscriptions(area: str | None = None):
    """List all subscriptions, optionally filtered by area."""
    if area:
        return get_subscriptions_for_area(area)
    return get_all_subscriptions()
