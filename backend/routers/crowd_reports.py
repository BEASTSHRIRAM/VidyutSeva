"""
Crowd-sourced outage report routes.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from database.supabase_client import get_crowd_reports
from agents.orchestrator import get_orchestrator

router = APIRouter(prefix="/reports", tags=["crowd_reports"])


class CrowdReportCreate(BaseModel):
    area_name: str
    description: str
    reporter_phone: str | None = None
    report_source: str = "web"


@router.post("")
async def submit_report(report: CrowdReportCreate):
    """
    Submit a crowd-sourced outage report.
    Auto-creates an outage if 3+ reports from the same area in 30 minutes.
    """
    orchestrator = get_orchestrator()
    result = await orchestrator.submit_crowd_report(
        area_name=report.area_name,
        description=report.description,
        reporter_phone=report.reporter_phone,
        report_source=report.report_source,
    )
    return result


@router.get("")
async def list_reports(area: str | None = None, limit: int = 50):
    """List crowd reports, optionally filtered by area."""
    return get_crowd_reports(area, limit)
