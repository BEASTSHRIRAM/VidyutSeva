"""
Outage CRUD routes.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
from database.supabase_client import (
    get_all_outages,
    get_active_outages,
    create_outage,
    update_outage,
    delete_outage,
)
from qdrant.vector_store import embed_outage, search_similar_outages

router = APIRouter(prefix="/outages", tags=["outages"])


class OutageCreate(BaseModel):
    area_name: str
    outage_type: str = "planned_maintenance"
    reason: str = ""
    start_time: str  # ISO format
    end_time: str | None = None
    status: str = "active"
    source: str = "manual"
    severity: int = 1


class OutageUpdate(BaseModel):
    area_name: str | None = None
    outage_type: str | None = None
    reason: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    status: str | None = None
    severity: int | None = None


@router.get("")
async def list_outages(status: str | None = None, area: str | None = None):
    """List outages with optional filters."""
    if area:
        return get_active_outages(area) if status == "active" else get_all_outages(status)
    return get_all_outages(status)


@router.get("/active")
async def list_active_outages(area: str | None = None):
    """List only active outages."""
    return get_active_outages(area)


@router.post("")
async def add_outage(outage: OutageCreate):
    """Create a new outage and embed into Qdrant."""
    data = outage.model_dump()
    record = create_outage(data)
    if record:
        embed_outage(record)
    return record


@router.put("/{outage_id}")
async def modify_outage(outage_id: str, outage: OutageUpdate):
    """Update an existing outage."""
    data = {k: v for k, v in outage.model_dump().items() if v is not None}
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    data["updated_at"] = datetime.utcnow().isoformat()
    record = update_outage(outage_id, data)
    if not record:
        raise HTTPException(status_code=404, detail="Outage not found")
    return record


@router.delete("/{outage_id}")
async def remove_outage(outage_id: str):
    """Delete an outage."""
    success = delete_outage(outage_id)
    if not success:
        raise HTTPException(status_code=404, detail="Outage not found")
    return {"deleted": True}


@router.get("/search")
async def search_outages(q: str, limit: int = 5):
    """Semantic search for outages via Qdrant."""
    results = search_similar_outages(q, limit=limit)
    return results
