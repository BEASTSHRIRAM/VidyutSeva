"""
Vapi voice webhook handler.
Receives user speech from Vapi → runs agent pipeline → returns response.
"""

import time
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


@router.post("/webhook/chat/completions")
async def vapi_custom_llm(request: Request):
    """
    OpenAI-compatible endpoint for Vapi's 'Custom LLM' setting.
    Vapi sends OpenAI formatted chat history, we return OpenAI formatted response.
    """
    body = await request.json()
    
    messages = body.get("messages", [])
    user_message = ""
    
    # Find the most recent user turn
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            # OpenAI structured multimodal array can be passed
            if isinstance(content, list):
                # Extract text parts
                texts = [
                    part.get("text", "") 
                    for part in content 
                    if isinstance(part, dict) and part.get("type", "") == "text"
                ]
                user_message = " ".join(texts)
            elif isinstance(content, str):
                user_message = content
            else:
                user_message = str(content)
            break
            
    if not user_message:
        user_message = "Hello"

    # Run agent pipeline
    try:
        orchestrator = get_orchestrator()
        result = await orchestrator.process_message(user_message)
        response_text = result["response"]
        
        # Flatten any structured response payload to pure string so Vapi TTS speaks words, not JSON
        if isinstance(response_text, list):
            response_text = " ".join(
                str(part.get("text", part)) if isinstance(part, dict) else str(part)
                for part in response_text
            )
        elif not isinstance(response_text, str):
            response_text = str(response_text)
            
    except Exception as e:
        error_msg = str(e).lower()
        if "429" in error_msg or "quota" in error_msg or "exhausted" in error_msg:
            response_text = (
                "I apologize, but my Gemini API key has hit the free-tier rate limit of 10 requests per minute. "
                "Because I am a complex multi-agent system, I consume requests quickly. "
                "Please wait 60 seconds before speaking again, or upgrade your Google AI Studio billing plan."
            )
        else:
            response_text = "I'm sorry, I encountered a critical error while processing your request. Please check your backend logs."
    
    # Return exactly matching OpenAI payload
    return {
        "id": "chatcmpl-vapi-custom",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "vidyutseva-custom",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": response_text
            },
            "finish_reason": "stop"
        }]
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
