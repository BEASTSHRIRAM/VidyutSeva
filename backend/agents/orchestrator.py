"""
Orchestrator — Chains Location → Outage → Diagnosis agents using AgentScope
SequentialPipeline and MsgHub for multi-agent coordination.

After response: embeds call into Qdrant + logs to Supabase.
Also handles crowd-detection logic (3+ reports = auto-flag).
"""

import asyncio
import json
from datetime import datetime, timezone

from agentscope.message import Msg
from agentscope.pipeline import SequentialPipeline, MsgHub

from agents.location_agent import (
    create_location_agent,
    parse_location_response,
)
from agents.outage_agent import create_outage_agent
from agents.diagnosis_agent import create_diagnosis_agent

from database.supabase_client import (
    log_call,
    create_crowd_report,
    count_recent_reports_for_area,
    create_outage,
    get_subscriptions_for_area,
    log_notification,
)
from qdrant.vector_store import (
    embed_call,
    embed_crowd_report,
    embed_outage,
)


class Orchestrator:
    """AgentScope multi-agent pipeline orchestrator for VidyutSeva."""

    def __init__(self):
        # Create ReActAgent instances
        self.location_agent = create_location_agent()
        self.outage_agent = create_outage_agent()
        self.diagnosis_agent = create_diagnosis_agent()

    async def process_message(self, user_message: str) -> dict:
        """
        Full pipeline using AgentScope MsgHub:
        1. LocationAgent extracts area from user speech (ReAct + tools)
        2. OutageAgent looks up DB + Qdrant (ReAct + tools)
        3. DiagnosisAgent generates advice (ReAct + tools)
        Then: embed call into Qdrant + log to Supabase.

        Returns: {
            "response": str,
            "area": str,
            "outage_found": bool,
            "diagnosis_type": str
        }
        """
        user_msg = Msg("user", user_message, "user")

        # --- Step 1: Location extraction ---
        location_response = await self.location_agent(user_msg)
        location = parse_location_response(location_response)
        area = location.get("area", "unknown")

        # --- Step 2: Outage lookup with MsgHub ---
        # Build context message for outage agent including location info
        outage_prompt = Msg(
            "user",
            (
                f"The user is located in: {area} (Bangalore).\n"
                f"User's original message: \"{user_message}\"\n\n"
                f"Please investigate all data sources for outage information "
                f"in {area} and provide a comprehensive analysis."
            ),
            "user",
        )
        outage_response = await self.outage_agent(outage_prompt)
        outage_analysis = (
            outage_response.content
            if hasattr(outage_response, "content")
            else str(outage_response)
        )

        # --- Step 3: Diagnosis with full context ---
        diagnosis_prompt = Msg(
            "user",
            (
                f"USER AREA: {area}\n"
                f"USER MESSAGE: {user_message}\n\n"
                f"=== OUTAGE AGENT ANALYSIS ===\n"
                f"{outage_analysis}\n\n"
                f"Based on all the above information, generate the final "
                f"voice response for the user. Use your tools to enrich "
                f"with BESCOM knowledge and historical restoration data."
            ),
            "user",
        )
        diagnosis_response = await self.diagnosis_agent(diagnosis_prompt)
        response_text = (
            diagnosis_response.content
            if hasattr(diagnosis_response, "content")
            else str(diagnosis_response)
        )

        # Determine diagnosis type from the analysis
        outage_found = any(
            keyword in outage_analysis.lower()
            for keyword in ["active outage", "outage found", "outages_found\": 1",
                            "outages_found\": 2", "outages_found\": 3"]
        )
        if outage_found:
            diagnosis_type = "area_outage"
        elif "crowd" in outage_analysis.lower() and "report" in outage_analysis.lower():
            diagnosis_type = "crowd_reported"
        else:
            diagnosis_type = "building_issue"

        # --- Step 4: Log & embed ---
        call_data = {
            "caller_area": area,
            "user_message": user_message,
            "ai_response": response_text[:2000],  # Truncate for DB
            "outage_found": outage_found,
            "diagnosis_type": diagnosis_type,
        }

        # Fire-and-forget logging (don't block the response)
        try:
            log_call(call_data)
            embed_call(call_data)
        except Exception as e:
            print(f"[Orchestrator] Logging error (non-fatal): {e}")

        return {
            "response": response_text,
            "area": area,
            "outage_found": outage_found,
            "diagnosis_type": diagnosis_type,
        }

    async def process_with_msghub(self, user_message: str) -> dict:
        """
        Alternative pipeline using MsgHub for full agent broadcast.
        All agents see each other's messages — useful for complex reasoning.
        """
        user_msg = Msg("user", user_message, "user")

        async with MsgHub(
            participants=[
                self.location_agent,
                self.outage_agent,
                self.diagnosis_agent,
            ],
            announcement=Msg(
                "system",
                (
                    "A Bangalore citizen needs help with an electricity issue. "
                    "LocationAgent: extract the area. "
                    "OutageAgent: lookup outage data for that area. "
                    "DiagnosisAgent: generate the final response."
                ),
                "system",
            ),
        ):
            # Sequential execution within MsgHub — each agent sees prior messages
            await self.location_agent(user_msg)
            await self.outage_agent()
            final_msg = await self.diagnosis_agent()

        response_text = (
            final_msg.content
            if hasattr(final_msg, "content")
            else str(final_msg)
        )

        return {
            "response": response_text,
            "area": "extracted_in_pipeline",
            "outage_found": False,
            "diagnosis_type": "msghub_pipeline",
        }

    async def submit_crowd_report(
        self,
        area_name: str,
        description: str,
        reporter_phone: str | None = None,
        report_source: str = "web",
    ) -> dict:
        """
        Submit a crowd-sourced outage report.
        If 3+ reports from the same area in 30 min → auto-create outage.
        """
        report_data = {
            "area_name": area_name,
            "description": description,
            "reporter_phone": reporter_phone,
            "report_source": report_source,
        }

        # Store in Supabase
        report = create_crowd_report(report_data)

        # Embed in Qdrant
        try:
            embed_crowd_report(report)
        except Exception as e:
            print(f"[Orchestrator] Crowd report embed error: {e}")

        # Check crowd detection threshold
        recent_count = count_recent_reports_for_area(area_name, minutes=30)
        auto_outage_created = False

        if recent_count >= 3:
            # Auto-create an outage from crowd signals
            outage_data = {
                "area_name": area_name,
                "outage_type": "emergency",
                "reason": f"Crowd-detected: {recent_count} citizen reports in 30 minutes",
                "start_time": datetime.now(timezone.utc).isoformat(),
                "status": "active",
                "source": "crowd_detected",
                "severity": 2,
            }
            outage = create_outage(outage_data)
            if outage:
                try:
                    embed_outage(outage)
                except Exception as e:
                    print(f"[Orchestrator] Outage embed error: {e}")
                auto_outage_created = True

                # Trigger proactive alerts
                await self._send_alerts(area_name, outage)

        return {
            "report_stored": bool(report),
            "reports_in_area": recent_count,
            "auto_outage_created": auto_outage_created,
        }

    async def _send_alerts(self, area_name: str, outage: dict) -> None:
        """
        Send proactive alerts to subscribers for the given area.
        Logs notifications to DB. In production, would integrate SMS/email APIs.
        """
        subscribers = get_subscriptions_for_area(area_name)

        for sub in subscribers:
            message = (
                f"⚡ VidyutSeva Alert: Power outage detected in {area_name}. "
                f"Reason: {outage.get('reason', 'Under investigation')}. "
                f"Stay updated at vidyutseva.in"
            )
            try:
                log_notification({
                    "subscription_id": sub["id"],
                    "outage_id": outage.get("id"),
                    "message": message,
                    "status": "sent",
                })
            except Exception as e:
                print(f"[Orchestrator] Notification log error: {e}")

        print(f"[Orchestrator] Sent {len(subscribers)} alerts for {area_name}")


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_orchestrator: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    """Get or create the singleton Orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator
