"""
PostgreSQL client for VidyutSeva.
All database operations go through this module using direct psycopg connection instead of the Supabase REST API.
"""

import os
from datetime import datetime, timedelta, timezone
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    """Return a new database connection."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL must be set in .env")
    return psycopg.connect(db_url, row_factory=dict_row)


# ---------------------------------------------------------------------------
# Helper queries
# ---------------------------------------------------------------------------

def get_active_outages(area_name: str | None = None) -> list[dict]:
    """Fetch active outages, optionally filtered by area name (case-insensitive)."""
    query = "SELECT * FROM outages WHERE status = 'active'"
    params = []
    if area_name:
        query += " AND area_name ILIKE %s"
        params.append(f"%{area_name}%")
    query += " ORDER BY created_at DESC"
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()

def get_all_outages(status: str | None = None, limit: int = 50) -> list[dict]:
    """Fetch outages with optional status filter."""
    query = "SELECT * FROM outages"
    params = []
    if status:
        query += " WHERE status = %s"
        params.append(status)
    query += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()

def create_outage(data: dict) -> dict:
    """Insert a new outage record."""
    keys = list(data.keys())
    values = list(data.values())
    placeholders = ", ".join(["%s"] * len(keys))
    cols = ", ".join(keys)
    query = f"INSERT INTO outages ({cols}) VALUES ({placeholders}) RETURNING *"
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, values)
            conn.commit()
            return cur.fetchone() or {}

def update_outage(outage_id: str, data: dict) -> dict:
    """Update an existing outage record."""
    if not data:
        return {}
        
    keys = list(data.keys())
    values = list(data.values())
    set_clause = ", ".join([f"{k} = %s" for k in keys])
    values.append(outage_id)
    query = f"UPDATE outages SET {set_clause} WHERE id = %s RETURNING *"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, values)
            conn.commit()
            return cur.fetchone() or {}

def delete_outage(outage_id: str) -> bool:
    """Delete an outage record."""
    query = "DELETE FROM outages WHERE id = %s RETURNING id"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (outage_id,))
            conn.commit()
            return cur.fetchone() is not None

def log_call(data: dict) -> dict:
    """Insert a call log."""
    keys = list(data.keys())
    values = list(data.values())
    placeholders = ", ".join(["%s"] * len(keys))
    cols = ", ".join(keys)
    query = f"INSERT INTO call_logs ({cols}) VALUES ({placeholders}) RETURNING *"
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, values)
            conn.commit()
            return cur.fetchone() or {}

def get_recent_calls(limit: int = 20) -> list[dict]:
    """Fetch recent call logs."""
    query = "SELECT * FROM call_logs ORDER BY call_timestamp DESC LIMIT %s"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (limit,))
            return cur.fetchall()

def get_areas() -> list[dict]:
    """Fetch all areas."""
    query = "SELECT * FROM areas ORDER BY name"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchall()

# ---------------------------------------------------------------------------
# Crowd Reports
# ---------------------------------------------------------------------------

def create_crowd_report(data: dict) -> dict:
    """Insert a crowd report."""
    keys = list(data.keys())
    values = list(data.values())
    placeholders = ", ".join(["%s"] * len(keys))
    cols = ", ".join(keys)
    query = f"INSERT INTO crowd_reports ({cols}) VALUES ({placeholders}) RETURNING *"
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, values)
            conn.commit()
            return cur.fetchone() or {}

def get_crowd_reports(area_name: str | None = None, limit: int = 50) -> list[dict]:
    """Fetch crowd reports, optionally filtered by area."""
    query = "SELECT * FROM crowd_reports"
    params = []
    if area_name:
        query += " WHERE area_name ILIKE %s"
        params.append(f"%{area_name}%")
    query += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()

def count_recent_reports_for_area(area_name: str, minutes: int = 30) -> int:
    """Count reports for an area in the last N minutes (for crowd-detection)."""
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
    query = "SELECT count(*) FROM crowd_reports WHERE area_name ILIKE %s AND created_at >= %s"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (f"%{area_name}%", cutoff))
            row = cur.fetchone()
            return row["count"] if row else 0

# ---------------------------------------------------------------------------
# Alert Subscriptions
# ---------------------------------------------------------------------------

def create_subscription(data: dict) -> dict:
    """Create an alert subscription."""
    keys = list(data.keys())
    values = list(data.values())
    placeholders = ", ".join(["%s"] * len(keys))
    cols = ", ".join(keys)
    query = f"INSERT INTO alert_subscriptions ({cols}) VALUES ({placeholders}) RETURNING *"
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, values)
            conn.commit()
            return cur.fetchone() or {}

def get_subscriptions_for_area(area_name: str) -> list[dict]:
    """Get active subscriptions for an area."""
    query = "SELECT * FROM alert_subscriptions WHERE area_name ILIKE %s AND is_active = True"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (f"%{area_name}%",))
            return cur.fetchall()

def get_all_subscriptions() -> list[dict]:
    """Get all subscriptions."""
    query = "SELECT * FROM alert_subscriptions ORDER BY created_at DESC"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchall()

def log_notification(data: dict) -> dict:
    """Log a sent notification."""
    keys = list(data.keys())
    values = list(data.values())
    placeholders = ", ".join(["%s"] * len(keys))
    cols = ", ".join(keys)
    query = f"INSERT INTO alert_notifications ({cols}) VALUES ({placeholders}) RETURNING *"
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, values)
            conn.commit()
            return cur.fetchone() or {}

def get_dashboard_summary() -> dict:
    """Aggregate dashboard stats."""
    
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0).isoformat()
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM outages WHERE status = 'active'")
            active_outages = (cur.fetchone() or {})["count"]
            
            cur.execute("SELECT count(*) FROM call_logs WHERE call_timestamp >= %s", (today_start,))
            calls_today = (cur.fetchone() or {})["count"]
            
            cur.execute("SELECT count(*) FROM crowd_reports WHERE verified = False")
            unverified_reports = (cur.fetchone() or {})["count"]
            
            cur.execute("SELECT count(*) FROM alert_subscriptions WHERE is_active = True")
            active_subscriptions = (cur.fetchone() or {})["count"]

    return {
        "active_outages": active_outages or 0,
        "calls_today": calls_today or 0,
        "unverified_reports": unverified_reports or 0,
        "active_subscriptions": active_subscriptions or 0,
    }
