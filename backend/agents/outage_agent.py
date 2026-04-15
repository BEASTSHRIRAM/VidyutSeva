"""
Outage Agent — AgentScope ReActAgent that looks up Supabase DB + Qdrant
for outage information using ReAct reasoning with tool calls.
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
# Tool functions — registered in Toolkit for ReAct reasoning
# ---------------------------------------------------------------------------

async def lookup_outage_db(area_name: str) -> ToolResponse:
    """Query the Supabase database for active outages in a given area.
    Returns matching outage records with type, reason, timing, and severity.

    Args:
        area_name: The locality/area name to search for (case-insensitive).

    Returns:
        ToolResponse with JSON array of active outage records.
    """
    from database.supabase_client import get_active_outages
    results = get_active_outages(area_name)
    return ToolResponse(
        content=[TextBlock(
            type="text",
            text=json.dumps({
                "source": "supabase_db",
                "area_queried": area_name,
                "outages_found": len(results),
                "outages": results,
            }, default=str),
        )],
    )


async def search_similar_outages(query: str) -> ToolResponse:
    """Semantic search for similar historical outages in the Qdrant vector store.
    Finds past outages with similar descriptions, areas, or patterns.

    Args:
        query: A natural language description of the outage situation to search for.

    Returns:
        ToolResponse with similar historical outage records ranked by relevance.
    """
    from qdrant.vector_store import search_similar_outages as qdrant_search
    results = qdrant_search(query, limit=5)
    return ToolResponse(
        content=[TextBlock(
            type="text",
            text=json.dumps({
                "source": "qdrant_outage_history",
                "query": query,
                "results_count": len(results),
                "similar_outages": results,
            }, default=str),
        )],
    )


async def search_past_calls(query: str) -> ToolResponse:
    """Search past caller interactions in call memory for pattern detection.
    Helps identify recurring issues in specific areas.

    Args:
        query: A natural language description to search past call logs.

    Returns:
        ToolResponse with similar past call interactions.
    """
    from qdrant.vector_store import search_call_history
    results = search_call_history(query, limit=3)
    return ToolResponse(
        content=[TextBlock(
            type="text",
            text=json.dumps({
                "source": "qdrant_call_memory",
                "query": query,
                "results_count": len(results),
                "past_calls": results,
            }, default=str),
        )],
    )


async def search_crowd_reports_tool(query: str) -> ToolResponse:
    """Search crowd-sourced outage reports submitted by citizens.
    Helps detect unreported outages from community signals.

    Args:
        query: Area or description to search crowd reports.

    Returns:
        ToolResponse with matching citizen reports.
    """
    from qdrant.vector_store import search_crowd_reports
    results = search_crowd_reports(query, limit=5)
    return ToolResponse(
        content=[TextBlock(
            type="text",
            text=json.dumps({
                "source": "qdrant_crowd_reports",
                "query": query,
                "results_count": len(results),
                "crowd_reports": results,
            }, default=str),
        )],
    )


async def count_area_reports(area_name: str) -> ToolResponse:
    """Count recent crowd reports for a specific area in the last 30 minutes.
    Useful for detecting crowd-signal outages (3+ reports = likely real outage).

    Args:
        area_name: The area to count recent reports for.

    Returns:
        ToolResponse with the count of recent reports.
    """
    from database.supabase_client import count_recent_reports_for_area
    count = count_recent_reports_for_area(area_name, minutes=30)
    return ToolResponse(
        content=[TextBlock(
            type="text",
            text=json.dumps({
                "area": area_name,
                "recent_report_count": count,
                "threshold_for_auto_outage": 3,
                "likely_real_outage": count >= 3,
            }),
        )],
    )


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an electricity outage lookup specialist for Bangalore (BESCOM utility).
You have access to multiple data sources via tools. Use ReAct reasoning to investigate outages.

REASONING STEPS (ReAct):
1. THINK: What data sources should I check for this area?
2. ACT: Use `lookup_outage_db` to check the primary outage database.
3. OBSERVE: Review DB results.
4. THINK: Were outages found? Should I check historical data for context?
5. ACT: Use `search_similar_outages` to find past patterns.
6. ACT: Use `search_crowd_reports_tool` to check citizen reports.
7. ACT: Use `count_area_reports` to check crowd-signal strength.
8. ACT: Use `search_past_calls` to see if others have called about this area.
9. OBSERVE: Synthesize ALL data sources.
10. RESPOND: Provide a comprehensive analysis with:
    - Whether active outages exist (DB confirmed)
    - Historical patterns (Qdrant similarity)
    - Community signals (crowd reports)
    - Your assessment of the situation

Be thorough. Check ALL sources before concluding. Be factual — only report what the data shows.
"""


def create_outage_agent() -> ReActAgent:
    """Factory: creates a configured Outage Lookup ReActAgent."""
    toolkit = Toolkit()
    toolkit.register_tool_function(lookup_outage_db)
    toolkit.register_tool_function(search_similar_outages)
    toolkit.register_tool_function(search_past_calls)
    toolkit.register_tool_function(search_crowd_reports_tool)
    toolkit.register_tool_function(count_area_reports)

    model = GeminiChatModel(
        model_name="gemini-2.5-flash-lite",
        api_key=os.getenv("GEMINI_API_KEY"),
        stream=False,
    )

    agent = ReActAgent(
        name="OutageAgent",
        sys_prompt=SYSTEM_PROMPT,
        model=model,
        formatter=GeminiChatFormatter(),
        toolkit=toolkit,
        memory=InMemoryMemory(),
    )

    return agent
