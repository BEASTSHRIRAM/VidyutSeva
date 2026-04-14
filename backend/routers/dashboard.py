"""
Dashboard summary routes.
"""

from fastapi import APIRouter
from database.supabase_client import (
    get_dashboard_summary,
    get_recent_calls,
    get_areas,
    get_active_outages,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
async def dashboard_summary():
    """Aggregate dashboard stats: active outages, calls today, unverified reports, subscriptions."""
    return get_dashboard_summary()


@router.get("/calls")
async def recent_calls(limit: int = 20):
    """Recent call logs."""
    return get_recent_calls(limit)


@router.get("/areas")
async def area_status():
    """All areas with their current outage status."""
    areas = get_areas()
    active_outages = get_active_outages()

    # Build area → outage map
    outage_map: dict[str, list] = {}
    for outage in active_outages:
        name = outage.get("area_name", "")
        outage_map.setdefault(name.lower(), []).append(outage)

    result = []
    for area in areas:
        area_name = area.get("name", "")
        outages_here = outage_map.get(area_name.lower(), [])

        if outages_here:
            # Highest severity outage determines status
            max_severity = max(o.get("severity", 1) for o in outages_here)
            status = "outage" if max_severity >= 2 else "warning"
        else:
            status = "normal"

        result.append({
            **area,
            "status": status,
            "active_outage_count": len(outages_here),
            "outages": outages_here,
        })

    return result
