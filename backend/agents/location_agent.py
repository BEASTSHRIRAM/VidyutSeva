"""
Location Agent — AgentScope ReActAgent that extracts area/locality
from user's spoken message using ReAct reasoning + tool calls.
"""

import os
import json
from agentscope.agent import ReActAgent
from agentscope.model import OpenAIChatModel
from agentscope.formatter import OpenAIChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.tool import Toolkit, ToolResponse, TextBlock
from agentscope.message import Msg
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Known Bangalore Areas (tool data source)
# ---------------------------------------------------------------------------

BANGALORE_AREAS = [
    "Koramangala", "Indiranagar", "Jayanagar", "Whitefield", "Rajajinagar",
    "Hebbal", "Malleshwaram", "BTM Layout", "HSR Layout", "Electronic City",
    "Marathahalli", "Yelahanka", "Banashankari", "JP Nagar", "Basavanagudi",
    "Sadashivanagar", "Vijayanagar", "RT Nagar", "Bellandur", "Sarjapur Road",
    "Majestic", "MG Road", "Brigade Road", "Richmond Town", "Wilson Garden",
    "Cox Town", "Frazer Town", "Shivajinagar", "Domlur", "HAL", "Ulsoor",
    "Seshadripuram", "Yeshwanthpur", "Peenya", "Nagarbhavi", "Kengeri",
    "Bannerghatta Road", "Silk Board", "Madiwala", "Bommanahalli", "Arekere",
]


# ---------------------------------------------------------------------------
# Tool functions for the ReAct agent
# ---------------------------------------------------------------------------

async def match_bangalore_area(user_text: str) -> ToolResponse:
    """Match the user's text against known Bangalore localities.
    Returns the best matching area name, or 'unknown' if no match found.

    Args:
        user_text: The raw text from the user mentioning a location.

    Returns:
        ToolResponse with matched area name and confidence.
    """
    text_lower = user_text.lower()
    matches = []
    for area in BANGALORE_AREAS:
        if area.lower() in text_lower:
            matches.append(area)

    if matches:
        # Return the longest match (most specific)
        best = max(matches, key=len)
        return ToolResponse(
            content=[TextBlock(
                type="text",
                text=json.dumps({
                    "area": best,
                    "city": "Bangalore",
                    "confidence": "high",
                    "all_matches": matches,
                }),
            )],
        )
    else:
        return ToolResponse(
            content=[TextBlock(
                type="text",
                text=json.dumps({
                    "area": "unknown",
                    "city": "Bangalore",
                    "confidence": "low",
                    "note": "No known Bangalore area matched. Use LLM reasoning to infer the locality.",
                }),
            )],
        )


async def extract_pincode(user_text: str) -> ToolResponse:
    """Extract a 6-digit Indian pincode from user text if present.

    Args:
        user_text: The raw text from the user.

    Returns:
        ToolResponse with the extracted pincode or null.
    """
    import re
    pincodes = re.findall(r"\b5600\d{2}\b", user_text)
    if pincodes:
        return ToolResponse(
            content=[TextBlock(type="text", text=json.dumps({"pincode": pincodes[0]}))],
        )
    return ToolResponse(
        content=[TextBlock(type="text", text=json.dumps({"pincode": None}))],
    )


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a location extraction specialist for Bangalore, India.
Your job is to extract the area/locality name from the user's message using the provided tools.

REASONING STEPS (ReAct):
1. THINK: What location clues are in the user's message?
2. ACT: Use `match_bangalore_area` to check against known localities.
3. ACT: Use `extract_pincode` to check for a pincode.
4. OBSERVE: Review the tool results.
5. RESPOND: Output a final JSON with the extracted location:
   {"area": "<area_name>", "city": "Bangalore", "pincode": "<pincode_or_null>"}

If the user mentions a landmark (e.g., "near Forum Mall"), map it to the closest area (Koramangala).
If the user is vague or says "my area", set area to "unknown".
Always return valid JSON as your final answer.
"""


def create_location_agent() -> ReActAgent:
    """Factory: creates a configured Location ReActAgent."""
    # Register tools
    toolkit = Toolkit()
    toolkit.register_tool_function(match_bangalore_area)
    toolkit.register_tool_function(extract_pincode)

    model = OpenAIChatModel(
        model_name="gpt-4o",
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    agent = ReActAgent(
        name="LocationAgent",
        sys_prompt=SYSTEM_PROMPT,
        model=model,
        formatter=OpenAIChatFormatter(),
        toolkit=toolkit,
        memory=InMemoryMemory(),
    )

    return agent


def parse_location_response(msg: Msg) -> dict:
    """Parse the location agent's response Msg into a structured dict."""
    content = msg.content if hasattr(msg, "content") else str(msg)
    try:
        # Try to extract JSON from the response
        if isinstance(content, str):
            # Find JSON in the response text
            import re
            json_match = re.search(r'\{[^}]+\}', content)
            if json_match:
                return json.loads(json_match.group())
        return {"area": "unknown", "city": "Bangalore", "pincode": None}
    except (json.JSONDecodeError, AttributeError):
        return {"area": "unknown", "city": "Bangalore", "pincode": None}
