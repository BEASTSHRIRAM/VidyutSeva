"""
Diagnosis Agent — AgentScope ReActAgent that generates actionable advice
based on outage data and historical context using ReAct reasoning.
"""

import os
import json
from agentscope.agent import ReActAgent
from agentscope.model import GeminiChatModel
from agentscope.formatter import GeminiChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.tool import Toolkit, ToolResponse
from agentscope.message import Msg, TextBlock
from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Tool functions — knowledge retrieval for diagnosis
# ---------------------------------------------------------------------------

async def search_bescom_knowledge(query: str) -> ToolResponse:
    """Search the BESCOM knowledge base for relevant policies, procedures,
    and guidelines that can help diagnose or advise the user.

    Args:
        query: Natural language query about BESCOM policies or procedures.

    Returns:
        ToolResponse with matching knowledge chunks from BESCOM docs.
    """
    from qdrant.vector_store import search_knowledge
    results = search_knowledge(query, limit=3)
    return ToolResponse(
        content=[TextBlock(
            type="text",
            text=json.dumps({
                "source": "bescom_knowledge_base",
                "query": query,
                "results_count": len(results),
                "knowledge_chunks": results,
            }, default=str),
        )],
    )


async def get_historical_restoration_time(area_name: str) -> ToolResponse:
    """Estimate restoration time based on historical outage data for an area.
    Analyzes past outages to predict how long a power cut typically lasts.

    Args:
        area_name: The area to check historical restoration times for.

    Returns:
        ToolResponse with estimated restoration time based on historical data.
    """
    from qdrant.vector_store import search_similar_outages
    results = search_similar_outages(
        f"{area_name} electricity outage restoration resolved", limit=10
    )

    # Analyze historical patterns
    if results:
        return ToolResponse(
            content=[TextBlock(
                type="text",
                text=json.dumps({
                    "area": area_name,
                    "historical_incidents": len(results),
                    "note": "Based on similar past incidents in this area and nearby areas.",
                    "sample_incidents": results[:3],
                }, default=str),
            )],
        )
    return ToolResponse(
        content=[TextBlock(
            type="text",
            text=json.dumps({
                "area": area_name,
                "historical_incidents": 0,
                "note": "No historical data available for restoration time estimation.",
            }),
        )],
    )


async def get_bescom_contact_info(issue_type: str) -> ToolResponse:
    """Get relevant BESCOM contact information and escalation paths
    based on the type of issue the user is experiencing.

    Args:
        issue_type: Type of issue - 'area_outage', 'building_issue', 'billing', 'new_connection'.

    Returns:
        ToolResponse with relevant contact info and escalation steps.
    """
    contacts = {
        "area_outage": {
            "primary": "1912 (BESCOM Helpline)",
            "online": "bescom.karnataka.gov.in",
            "escalation": "If not resolved in 4 hours, file complaint at BESCOM divisional office",
            "tip": "Note down your complaint number for follow-up",
        },
        "building_issue": {
            "primary": "Contact your building electrician first",
            "secondary": "1912 - Request a lineman visit for your specific address",
            "tip": "Check MCB/circuit breaker, meter box, and ask neighbors before calling",
        },
        "billing": {
            "primary": "1912 (BESCOM Helpline)",
            "online": "bescom.karnataka.gov.in/billing",
            "subdivision_office": "Visit nearest BESCOM subdivision office with recent bill",
        },
        "new_connection": {
            "primary": "bescom.karnataka.gov.in/new-connection",
            "phone": "1912",
        },
    }
    info = contacts.get(issue_type, contacts["area_outage"])
    return ToolResponse(
        content=[TextBlock(type="text", text=json.dumps(info))],
    )


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are VidyutSeva, a helpful and empathetic AI electricity support assistant for Bangalore citizens.
You generate the FINAL response that will be spoken to the user via voice call.

You receive context from previous agents (location data, outage lookup results).
Use your tools for additional knowledge retrieval, then generate your diagnosis.

REASONING STEPS (ReAct):
1. THINK: Analyze the outage data provided. Is there an active outage, crowd-reported issue, or building-specific problem?
2. ACT: Use `search_bescom_knowledge` for relevant BESCOM policies/procedures.
3. ACT: Use `get_historical_restoration_time` to estimate when power might return.
4. ACT: Use `get_bescom_contact_info` to get relevant escalation paths.
5. OBSERVE: Combine all data.
6. RESPOND: Generate the final user-facing response.

RESPONSE RULES:
- If ACTIVE OUTAGE found: State type, reason, estimated restoration, and advice.
- If NO OUTAGE found: Explain it's likely building-specific. Give troubleshooting steps:
  a) Check main circuit breaker / MCB box
  b) Check electricity meter for errors
  c) Ask neighbors if they also lost power
  d) Contact building electrician if only your building is affected
  e) Call BESCOM 1912 and request lineman for YOUR specific address
- If CROWD REPORTS exist but no official outage: Mention community signals, suggest reporting.
- Use historical data: "Based on past incidents, restoration typically takes X hours."
- TONE: Professional yet warm. Concise (under 200 words — this is for voice).
- Always end with: "Is there anything else I can help you with regarding your electricity?"
"""


def create_diagnosis_agent() -> ReActAgent:
    """Factory: creates a configured Diagnosis ReActAgent."""
    toolkit = Toolkit()
    toolkit.register_tool_function(search_bescom_knowledge)
    toolkit.register_tool_function(get_historical_restoration_time)
    toolkit.register_tool_function(get_bescom_contact_info)

    model = GeminiChatModel(
        model_name="gemini-2.5-flash-lite",
        api_key=os.getenv("GEMINI_API_KEY"),
        stream=False,
    )

    agent = ReActAgent(
        name="DiagnosisAgent",
        sys_prompt=SYSTEM_PROMPT,
        model=model,
        formatter=GeminiChatFormatter(),
        toolkit=toolkit,
        memory=InMemoryMemory(),
    )

    return agent
