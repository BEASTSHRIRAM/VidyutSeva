"""
EscalationAgent — AgentScope ReActAgent that handles hardware fault detection
and lineman dispatch pipeline.

ReAct Flow:
  1. THINK: Is this a hardware fault? Use classify_hardware_fault tool.
  2. ACT: find_nearest_lineman — Haversine search from DB.
  3. ACT: push_escalation_to_dashboard — write to escalations table.
  4. ACT: trigger_lineman_call — Vapi outbound call.
  5. RESPOND: Summary of what was escalated and to whom.
"""

import os
import json
import logging

from agentscope.agent import ReActAgent
from agentscope.model import GeminiChatModel
from agentscope.formatter import GeminiChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.tool import Toolkit, ToolResponse
from agentscope.message import Msg, TextBlock
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Utility: Haversine distance
# ---------------------------------------------------------------------------

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import radians, cos, sin, asin, sqrt
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371 * 2 * asin(sqrt(a))


# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------

async def classify_hardware_fault(report_text: str) -> ToolResponse:
    """Classify whether an electricity complaint describes a hardware fault.
    Hardware faults include: transformer failure, fallen/burnt cables, broken poles,
    damaged meters, sparking/burning equipment.

    Args:
        report_text: The citizen's complaint text describing the electricity issue.

    Returns:
        ToolResponse with JSON: {is_hardware_fault, fault_type, confidence, suggested_action}
    """
    # Keyword-based fast-path to avoid extra LLM call
    text_lower = report_text.lower()
    hw_keywords = {
        "transformer": "transformer",
        "cable": "cable",
        "wire": "cable",
        "pole": "pole",
        "spark": "cable",
        "burn": "cable",
        "fire": "cable",
        "fallen": "pole",
        "broke": "other",
        "damage": "other",
        "explosion": "transformer",
        "blast": "transformer",
        "smoke": "transformer",
    }
    matched_type = None
    for kw, fault_type in hw_keywords.items():
        if kw in text_lower:
            matched_type = fault_type
            break

    if matched_type:
        result = {
            "is_hardware_fault": True,
            "fault_type": matched_type,
            "confidence": 0.85,
            "suggested_action": f"Dispatch lineman for {matched_type} inspection immediately",
        }
    else:
        result = {
            "is_hardware_fault": False,
            "fault_type": None,
            "confidence": 0.70,
            "suggested_action": "Monitor — appears to be a non-hardware issue (billing/planned/tripping)",
        }

    return ToolResponse(
        content=[TextBlock(type="text", text=json.dumps(result))],
    )


async def find_nearest_lineman(
    latitude: float,
    longitude: float,
    area_hint: str = "",
) -> ToolResponse:
    """Find the nearest available lineman for a given GPS location.
    Uses Haversine formula to calculate distances from all available linemen.

    Args:
        latitude: Latitude of the complaint location.
        longitude: Longitude of the complaint location.
        area_hint: Area name to optionally filter candidates first.

    Returns:
        ToolResponse with JSON: {lineman_id, name, phone_number, area, distance_km, ...}
    """
    try:
        from database.supabase_client import get_all_linemen
        linemen = get_all_linemen()

        if not linemen:
            return ToolResponse(
                content=[TextBlock(type="text", text=json.dumps({"error": "No linemen found in database"}))],
            )

        # Try area-filtered first
        candidates = linemen
        if area_hint:
            filtered = [l for l in linemen if area_hint.lower() in (l.get("area") or "").lower()]
            if filtered:
                candidates = filtered

        best = None
        best_dist = float("inf")
        for lm in candidates:
            if not lm.get("is_available", True):
                continue
            dist = _haversine_km(
                latitude, longitude,
                float(lm.get("latitude", 0)),
                float(lm.get("longitude", 0)),
            )
            if dist < best_dist:
                best_dist = dist
                best = {**lm, "distance_km": round(dist, 2)}

        if not best:
            # Fallback: pick from all (ignore availability)
            for lm in linemen:
                dist = _haversine_km(latitude, longitude,
                    float(lm.get("latitude", 0)), float(lm.get("longitude", 0)))
                if dist < best_dist:
                    best_dist = dist
                    best = {**lm, "distance_km": round(dist, 2)}

        return ToolResponse(
            content=[TextBlock(type="text", text=json.dumps(best, default=str))],
        )
    except Exception as e:
        logger.error(f"[EscalationAgent] find_nearest_lineman error: {e}")
        return ToolResponse(
            content=[TextBlock(type="text", text=json.dumps({"error": str(e)}))],
        )


async def push_escalation_to_dashboard(
    complaint_id: str,
    report_text: str,
    fault_type: str,
    confidence: float,
    lineman_id: str,
    lineman_name: str,
    lineman_phone: str,
    distance_km: float,
) -> ToolResponse:
    """Push an escalation record to the BESCOM employee dashboard (DB).
    Also marks the complaint as escalated.

    Args:
        complaint_id: UUID of the complaint being escalated.
        report_text: The original complaint text (first 500 chars).
        fault_type: Type of hardware fault detected.
        confidence: Confidence score from classification (0.0-1.0).
        lineman_id: UUID of the assigned lineman.
        lineman_name: Full name of the lineman.
        lineman_phone: Phone number of the lineman.
        distance_km: Distance between complaint and lineman in km.

    Returns:
        ToolResponse with escalation record JSON.
    """
    try:
        from database.supabase_client import create_escalation, update_complaint
        escalation_data = {
            "complaint_id": complaint_id if complaint_id != "UNKNOWN" else None,
            "report_text": report_text[:500],
            "fault_type": fault_type,
            "confidence": confidence,
            "lineman_id": lineman_id if lineman_id != "UNKNOWN" else None,
            "lineman_name": lineman_name,
            "lineman_phone": lineman_phone,
            "distance_km": distance_km,
            "status": "escalated",
            "call_status": "pending",
        }
        record = create_escalation(escalation_data)

        # Mark complaint as escalated
        if complaint_id and complaint_id != "UNKNOWN":
            try:
                update_complaint(complaint_id, {"escalated": True, "status": "acknowledged"})
            except Exception:
                pass

        return ToolResponse(
            content=[TextBlock(type="text", text=json.dumps({
                "success": True,
                "escalation_id": str(record.get("id", "")) if record else None,
                "message": f"Escalation pushed to BESCOM dashboard. Assigned to {lineman_name}.",
            }, default=str))],
        )
    except Exception as e:
        logger.error(f"[EscalationAgent] push_escalation error: {e}")
        return ToolResponse(
            content=[TextBlock(type="text", text=json.dumps({"success": False, "error": str(e)}))],
        )


async def trigger_lineman_call(
    lineman_phone: str,
    lineman_name: str,
    complaint_area: str,
    fault_type: str,
    complaint_id: str,
    report_text: str,
) -> ToolResponse:
    """Trigger an outbound Vapi AI call to notify the lineman of the hardware fault.
    The AI call will brief the lineman on the issue and location.

    Args:
        lineman_phone: The lineman's phone number (digits only, will be formatted +91XXXXXXXXXX).
        lineman_name: Name of the lineman for personalization.
        complaint_area: The area where the fault was reported.
        fault_type: Type of hardware fault (transformer/cable/pole/etc).
        complaint_id: Complaint ID for reference (e.g. VSEVA-260416-7843).
        report_text: Short description of the issue (max 200 chars).

    Returns:
        ToolResponse with call status JSON: {status, call_id, message}
    """
    vapi_key = os.getenv("VAPI_API_KEY", "")
    assistant_id = os.getenv("VAPI_LINEMAN_ASSISTANT_ID", "")
    phone_number_id = os.getenv("VAPI_PHONE_NUMBER_ID", "")

    if not vapi_key or vapi_key.startswith("your_"):
        logger.info("[EscalationAgent] Vapi call skipped — VAPI_API_KEY not configured")
        return ToolResponse(
            content=[TextBlock(type="text", text=json.dumps({
                "status": "skipped",
                "message": "Vapi call skipped — VAPI_API_KEY not configured. In production, lineman would be called automatically.",
            }))],
        )

    try:
        import requests

        # Format phone number for India
        phone = lineman_phone.replace(" ", "").replace("-", "")
        if not phone.startswith("+"):
            phone = "+91" + phone

        headers = {
            "Authorization": f"Bearer {vapi_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "phoneNumberId": phone_number_id,
            "customer": {"number": phone, "name": lineman_name},
            "assistantId": assistant_id,
            "assistantOverrides": {
                "variableValues": {
                    "lineman_name": lineman_name,
                    "location": complaint_area,
                    "fault_type": fault_type,
                    "complaint_id": complaint_id,
                    "report_summary": report_text[:200],
                },
            },
        }

        resp = requests.post(
            "https://api.vapi.ai/call", headers=headers, json=payload, timeout=15
        )
        resp.raise_for_status()
        data = resp.json()

        return ToolResponse(
            content=[TextBlock(type="text", text=json.dumps({
                "status": "calling",
                "call_id": data.get("id", ""),
                "message": f"Outbound Vapi call initiated to {lineman_name} at {phone}",
            }))],
        )
    except Exception as e:
        logger.error(f"[EscalationAgent] Vapi call error: {e}")
        return ToolResponse(
            content=[TextBlock(type="text", text=json.dumps({
                "status": "failed",
                "error": str(e),
                "message": "Vapi call failed — see error details.",
            }))],
        )


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are the EscalationAgent for VidyutSeva, BESCOM's AI dispatch system for Bangalore.

Your job: Analyze incoming electricity fault reports and dispatch linemen to hardware faults automatically.

REASONING STEPS (ReAct):
1. THINK: Read the complaint. Does it sound like a hardware fault (transformer, cable, pole, sparks, smoke, fire)?
2. ACT: Call `classify_hardware_fault` with the complaint text.
3. OBSERVE: If is_hardware_fault=false OR confidence < 0.55 → respond "No escalation needed" and STOP.
4. ACT: Call `find_nearest_lineman` with the complaint's lat/lon and area.
5. OBSERVE: Get the nearest available lineman details.
6. ACT: Call `push_escalation_to_dashboard` to notify BESCOM dashboard.
7. ACT: Call `trigger_lineman_call` to dispatch the lineman via Vapi phone call.
8. RESPOND: A concise summary of the escalation: what was detected, who was dispatched, call status.

IMPORTANT:
- If no lat/lon is provided, use Bangalore center coordinates: lat=12.9716, lon=77.5946
- Always complete all 4 tool calls for a confirmed hardware fault
- Report the distance_km to show efficiency
- Format the final response clearly for the BESCOM admin dashboard
"""


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------

def create_escalation_agent() -> ReActAgent:
    """Factory: creates a configured EscalationAgent ReActAgent."""
    toolkit = Toolkit()
    toolkit.register_tool_function(classify_hardware_fault)
    toolkit.register_tool_function(find_nearest_lineman)
    toolkit.register_tool_function(push_escalation_to_dashboard)
    toolkit.register_tool_function(trigger_lineman_call)

    model = GeminiChatModel(
        model_name="gemini-2.5-flash-lite",
        api_key=os.getenv("GEMINI_API_KEY"),
        stream=False,
    )

    agent = ReActAgent(
        name="EscalationAgent",
        sys_prompt=SYSTEM_PROMPT,
        model=model,
        formatter=GeminiChatFormatter(),
        toolkit=toolkit,
        memory=InMemoryMemory(),
    )

    return agent


# ---------------------------------------------------------------------------
# Convenience async wrapper for orchestrator
# ---------------------------------------------------------------------------

async def run_escalation_pipeline(complaint: dict) -> dict:
    """
    Create a fresh EscalationAgent instance and process a complaint.
    Called by the orchestrator or complaints router.

    Args:
        complaint: {id, complaint_id, text, area, latitude, longitude, ...}

    Returns:
        {escalated: bool, message: str, agent_response: str}
    """
    agent = create_escalation_agent()

    area = complaint.get("area", "Bangalore")
    lat = complaint.get("latitude") or 12.9716
    lon = complaint.get("longitude") or 77.5946

    prompt = (
        f"COMPLAINT ID: {complaint.get('complaint_id', 'UNKNOWN')}\n"
        f"UUID: {complaint.get('id', 'UNKNOWN')}\n"
        f"AREA: {area}\n"
        f"COORDINATES: lat={lat}, lon={lon}\n"
        f"SOURCE: {complaint.get('source', 'app')}\n\n"
        f"COMPLAINT TEXT:\n{complaint.get('text', '')}\n\n"
        f"Please analyze this complaint and escalate if it is a hardware fault."
    )

    user_msg = Msg("user", prompt, "user")

    try:
        response = await agent(user_msg)
        content = response.content if hasattr(response, "content") else str(response)

        # Determine if escalation happened from response text
        escalated = any(
            kw in str(content).lower()
            for kw in ["escalated", "dispatched", "calling", "lineman assigned", "outbound call"]
        )

        return {
            "escalated": escalated,
            "message": str(content)[:500],
            "agent_response": str(content),
        }
    except Exception as e:
        logger.error(f"[EscalationAgent] Pipeline error: {e}")
        return {
            "escalated": False,
            "message": f"Escalation pipeline error: {e}",
            "agent_response": "",
        }
