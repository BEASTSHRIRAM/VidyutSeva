"""
Vapi voice webhook handler.
Receives user speech from Vapi → runs agent pipeline → returns response.
"""

from fastapi import APIRouter, Request
from agents.orchestrator import get_orchestrator

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/webhook")
async def vapi_webhook(request: Request):
    """
    Vapi webhook endpoint.
    Expects JSON: { "message": { "content": "user speech text" } }
    Returns: { "role": "assistant", "content": "AI response" }
    """
    body = await request.json()

    # Extract user message from Vapi payload
    # Vapi sends different event types — we handle the "function-call" and
    # "conversation-update" patterns
    user_message = ""

    if "message" in body:
        msg = body["message"]
        if isinstance(msg, dict):
            user_message = msg.get("content", "") or msg.get("text", "")
        elif isinstance(msg, str):
            user_message = msg
    elif "transcript" in body:
        user_message = body["transcript"]
    elif "text" in body:
        user_message = body["text"]

    if not user_message:
        return {
            "role": "assistant",
            "content": (
                "I didn't catch that. Could you please tell me your area "
                "and describe your electricity issue?"
            ),
        }

    # Run agent pipeline
    orchestrator = get_orchestrator()
    result = await orchestrator.process_message(user_message)

    return {
        "role": "assistant",
        "content": result["response"],
        "metadata": {
            "area": result.get("area"),
            "outage_found": result.get("outage_found"),
            "diagnosis_type": result.get("diagnosis_type"),
        },
    }


@router.post("/test")
async def test_voice(request: Request):
    """
    Test endpoint — accepts plain text and runs the pipeline.
    POST /voice/test with { "message": "I live in Koramangala, power cut" }
    """
    body = await request.json()
    user_message = body.get("message", "")

    if not user_message:
        return {"error": "message field is required"}

    orchestrator = get_orchestrator()
    result = await orchestrator.process_message(user_message)
    return result
