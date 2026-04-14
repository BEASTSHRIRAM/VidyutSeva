"""
Supabase client singleton for VidyutSeva.
All database operations go through this module.
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_client: Client | None = None


def get_supabase() -> Client:
    """Return a singleton Supabase client."""
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_KEY must be set in .env"
            )
        _client = create_client(url, key)
    return _client


# ---------------------------------------------------------------------------
# Helper queries
# ---------------------------------------------------------------------------

def get_active_outages(area_name: str | None = None) -> list[dict]:
    """Fetch active outages, optionally filtered by area name (case-insensitive)."""
    db = get_supabase()
    query = db.table("outages").select("*").eq("status", "active")
    if area_name:
        query = query.ilike("area_name", f"%{area_name}%")
    resp = query.order("created_at", desc=True).execute()
    return resp.data


def get_all_outages(status: str | None = None, limit: int = 50) -> list[dict]:
    """Fetch outages with optional status filter."""
    db = get_supabase()
    query = db.table("outages").select("*")
    if status:
        query = query.eq("status", status)
    resp = query.order("created_at", desc=True).limit(limit).execute()
    return resp.data


def create_outage(data: dict) -> dict:
    """Insert a new outage record."""
    db = get_supabase()
    resp = db.table("outages").insert(data).execute()
    return resp.data[0] if resp.data else {}


def update_outage(outage_id: str, data: dict) -> dict:
    """Update an existing outage record."""
    db = get_supabase()
    resp = db.table("outages").update(data).eq("id", outage_id).execute()
    return resp.data[0] if resp.data else {}


def delete_outage(outage_id: str) -> bool:
    """Delete an outage record."""
    db = get_supabase()
    resp = db.table("outages").delete().eq("id", outage_id).execute()
    return bool(resp.data)


def log_call(data: dict) -> dict:
    """Insert a call log."""
    db = get_supabase()
    resp = db.table("call_logs").insert(data).execute()
    return resp.data[0] if resp.data else {}


def get_recent_calls(limit: int = 20) -> list[dict]:
    """Fetch recent call logs."""
    db = get_supabase()
    resp = (
        db.table("call_logs")
        .select("*")
        .order("call_timestamp", desc=True)
        .limit(limit)
        .execute()
    )
    return resp.data


def get_areas() -> list[dict]:
    """Fetch all areas."""
    db = get_supabase()
    resp = db.table("areas").select("*").order("name").execute()
    return resp.data


# ---------------------------------------------------------------------------
# Crowd Reports
# ---------------------------------------------------------------------------

def create_crowd_report(data: dict) -> dict:
    """Insert a crowd report."""
    db = get_supabase()
    resp = db.table("crowd_reports").insert(data).execute()
    return resp.data[0] if resp.data else {}


def get_crowd_reports(area_name: str | None = None, limit: int = 50) -> list[dict]:
    """Fetch crowd reports, optionally filtered by area."""
    db = get_supabase()
    query = db.table("crowd_reports").select("*")
    if area_name:
        query = query.ilike("area_name", f"%{area_name}%")
    resp = query.order("created_at", desc=True).limit(limit).execute()
    return resp.data


def count_recent_reports_for_area(area_name: str, minutes: int = 30) -> int:
    """Count reports for an area in the last N minutes (for crowd-detection)."""
    from datetime import datetime, timedelta, timezone
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
    db = get_supabase()
    resp = (
        db.table("crowd_reports")
        .select("id", count="exact")
        .ilike("area_name", f"%{area_name}%")
        .gte("created_at", cutoff)
        .execute()
    )
    return resp.count or 0


# ---------------------------------------------------------------------------
# Alert Subscriptions
# ---------------------------------------------------------------------------

def create_subscription(data: dict) -> dict:
    """Create an alert subscription."""
    db = get_supabase()
    resp = db.table("alert_subscriptions").insert(data).execute()
    return resp.data[0] if resp.data else {}


def get_subscriptions_for_area(area_name: str) -> list[dict]:
    """Get active subscriptions for an area."""
    db = get_supabase()
    resp = (
        db.table("alert_subscriptions")
        .select("*")
        .ilike("area_name", f"%{area_name}%")
        .eq("is_active", True)
        .execute()
    )
    return resp.data


def get_all_subscriptions() -> list[dict]:
    """Get all subscriptions."""
    db = get_supabase()
    resp = db.table("alert_subscriptions").select("*").order("created_at", desc=True).execute()
    return resp.data


def log_notification(data: dict) -> dict:
    """Log a sent notification."""
    db = get_supabase()
    resp = db.table("alert_notifications").insert(data).execute()
    return resp.data[0] if resp.data else {}


def get_dashboard_summary() -> dict:
    """Aggregate dashboard stats."""
    db = get_supabase()
    from datetime import datetime, timezone

    active = db.table("outages").select("id", count="exact").eq("status", "active").execute()
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0).isoformat()
    calls_today = (
        db.table("call_logs")
        .select("id", count="exact")
        .gte("call_timestamp", today_start)
        .execute()
    )
    reports = (
        db.table("crowd_reports")
        .select("id", count="exact")
        .eq("verified", False)
        .execute()
    )
    subs = db.table("alert_subscriptions").select("id", count="exact").eq("is_active", True).execute()

    return {
        "active_outages": active.count or 0,
        "calls_today": calls_today.count or 0,
        "unverified_reports": reports.count or 0,
        "active_subscriptions": subs.count or 0,
    }
