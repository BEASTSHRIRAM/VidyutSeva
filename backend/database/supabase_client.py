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


# ---------------------------------------------------------------------------
# Users / Auth
# ---------------------------------------------------------------------------

def get_user_by_phone(phone_number: str) -> dict | None:
    """Fetch a user by phone number."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE phone_number = %s", (phone_number,))
            return cur.fetchone()


def upsert_user_otp(phone_number: str, otp: str, expires_at: str) -> dict:
    """Create user if not exists, then set OTP."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (phone_number, otp_code, otp_expires_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (phone_number) DO UPDATE
                    SET otp_code = EXCLUDED.otp_code,
                        otp_expires_at = EXCLUDED.otp_expires_at,
                        updated_at = NOW()
                RETURNING *
            """, (phone_number, otp, expires_at))
            conn.commit()
            return cur.fetchone() or {}


def verify_user_otp(phone_number: str, name: str | None = None) -> dict:
    """Mark user as verified, clear OTP, optionally set name."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            if name:
                cur.execute("""
                    UPDATE users
                    SET is_verified = TRUE, otp_code = NULL, otp_expires_at = NULL,
                        name = COALESCE(%s, name), updated_at = NOW()
                    WHERE phone_number = %s
                    RETURNING *
                """, (name, phone_number))
            else:
                cur.execute("""
                    UPDATE users
                    SET is_verified = TRUE, otp_code = NULL, otp_expires_at = NULL, updated_at = NOW()
                    WHERE phone_number = %s
                    RETURNING *
                """, (phone_number,))
            conn.commit()
            return cur.fetchone() or {}


def merge_anonymous_complaints(phone_number: str, user_id: str) -> int:
    """Link all anonymous complaints for a phone to the now-registered user. Returns rows updated."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE complaints SET user_id = %s
                WHERE phone_number = %s AND user_id IS NULL
            """, (user_id, phone_number))
            conn.commit()
            return cur.rowcount


# ---------------------------------------------------------------------------
# Complaints
# ---------------------------------------------------------------------------

def create_complaint(data: dict) -> dict:
    """Insert a new complaint record."""
    keys = list(data.keys())
    values = list(data.values())
    placeholders = ", ".join(["%s"] * len(keys))
    cols = ", ".join(keys)
    query = f"INSERT INTO complaints ({cols}) VALUES ({placeholders}) RETURNING *"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, values)
            conn.commit()
            return cur.fetchone() or {}


def get_complaints(
    area: str | None = None,
    status: str | None = None,
    sort: str = "upvotes",
    limit: int = 50,
) -> list[dict]:
    """Fetch complaints with optional filters, sorted by upvotes or recency."""
    conditions = []
    params: list = []
    if area:
        conditions.append("area ILIKE %s")
        params.append(f"%{area}%")
    if status:
        conditions.append("status = %s")
        params.append(status)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    order = "upvote_count DESC, created_at DESC" if sort == "upvotes" else "created_at DESC"
    params.append(limit)
    query = f"SELECT * FROM complaints {where} ORDER BY {order} LIMIT %s"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()


def get_complaint_by_id(complaint_id: str) -> dict | None:
    """Fetch by UUID or short complaint_id (VSEVA-...)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Try UUID first, then complaint_id string
            cur.execute(
                "SELECT * FROM complaints WHERE id::text = %s OR complaint_id = %s",
                (complaint_id, complaint_id),
            )
            return cur.fetchone()


def update_complaint(complaint_id: str, data: dict) -> dict | None:
    """Update complaint by UUID."""
    if not data:
        return None
    keys = list(data.keys())
    values = list(data.values())
    set_clause = ", ".join([f"{k} = %s" for k in keys])
    values.append(complaint_id)
    query = f"UPDATE complaints SET {set_clause}, updated_at = NOW() WHERE id::text = %s RETURNING *"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, values)
            conn.commit()
            return cur.fetchone()


def toggle_upvote(complaint_id: str, user_id: str) -> dict:
    """Toggle upvote for a user on a complaint. Returns {upvoted, upvote_count}."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Check existing upvote
            cur.execute(
                "SELECT id FROM complaint_upvotes WHERE complaint_id::text = %s AND user_id::text = %s",
                (complaint_id, user_id),
            )
            existing = cur.fetchone()

            if existing:
                # Remove upvote
                cur.execute(
                    "DELETE FROM complaint_upvotes WHERE complaint_id::text = %s AND user_id::text = %s",
                    (complaint_id, user_id),
                )
                cur.execute(
                    "UPDATE complaints SET upvote_count = GREATEST(upvote_count - 1, 0) WHERE id::text = %s RETURNING upvote_count",
                    (complaint_id,),
                )
                count_row = cur.fetchone()
                conn.commit()
                return {"upvoted": False, "upvote_count": count_row["upvote_count"] if count_row else 0}
            else:
                # Add upvote
                cur.execute(
                    "INSERT INTO complaint_upvotes (complaint_id, user_id) VALUES (%s::uuid, %s::uuid)",
                    (complaint_id, user_id),
                )
                cur.execute(
                    "UPDATE complaints SET upvote_count = upvote_count + 1 WHERE id::text = %s RETURNING upvote_count",
                    (complaint_id,),
                )
                count_row = cur.fetchone()
                conn.commit()
                return {"upvoted": True, "upvote_count": count_row["upvote_count"] if count_row else 0}


# ---------------------------------------------------------------------------
# Escalations
# ---------------------------------------------------------------------------

def create_escalation(data: dict) -> dict:
    """Insert an escalation record."""
    keys = list(data.keys())
    values = list(data.values())
    placeholders = ", ".join(["%s"] * len(keys))
    cols = ", ".join(keys)
    query = f"INSERT INTO escalations ({cols}) VALUES ({placeholders}) RETURNING *"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, values)
            conn.commit()
            return cur.fetchone() or {}


def get_escalations(limit: int = 50) -> list[dict]:
    """Fetch escalations sorted by most recent, with complaint join."""
    query = """
        SELECT e.*,
               c.complaint_id AS complaint_ref,
               c.area AS complaint_area,
               c.text AS complaint_text,
               c.upvote_count
        FROM escalations e
        LEFT JOIN complaints c ON c.id = e.complaint_id
        ORDER BY e.escalated_at DESC
        LIMIT %s
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (limit,))
            return cur.fetchall()


# ---------------------------------------------------------------------------
# Linemen
# ---------------------------------------------------------------------------

def get_all_linemen() -> list[dict]:
    """Fetch all linemen from DB."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM linemen ORDER BY area")
            return cur.fetchall()
