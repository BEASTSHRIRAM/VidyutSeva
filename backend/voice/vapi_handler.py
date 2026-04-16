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


@router.post("/chat")
async def chat_message(request: Request):
    """
    Chat endpoint — same as /test but also runs escalation if hardware fault is detected.
    Used by the animated chat UI.
    POST /voice/chat with { "message": "...", "area": "...", "lat": 0, "lon": 0 }
    """
    from fastapi.responses import JSONResponse

    body = await request.json()
    user_message = body.get("message", "")
    area = body.get("area", "")
    lat = body.get("lat")
    lon = body.get("lon")

    if not user_message:
        return JSONResponse({"error": "message field is required"}, status_code=400)

    orchestrator = get_orchestrator()
    result = await orchestrator.process_message(user_message)

    # Run escalation in background for hardware faults
    import asyncio
    from agents.escalation_agent import run_escalation_pipeline

    complaint = {
        "id": None,
        "complaint_id": "CHAT-QUERY",
        "text": user_message,
        "area": area or result.get("area", "Bangalore"),
        "latitude": lat,
        "longitude": lon,
        "source": "chat",
    }
    # Fire and forget
    try:
        asyncio.create_task(run_escalation_pipeline(complaint))
    except RuntimeError:
        pass

    return {**result, "escalation_triggered": True}


@router.get("/chat/stream")
async def chat_stream(message: str, area: str = "", lat: float = 12.9716, lon: float = 77.5946):
    """
    SSE streaming endpoint — yields agent stage events as the pipeline runs.
    GET /voice/chat/stream?message=...&area=...
    Frontend connects and receives JSON events per agent stage.

    Event format per line:  data: {"stage": "location", "status": "done", "result": {...}}
    """
    import json
    import asyncio
    from fastapi.responses import StreamingResponse
    from agents.location_agent import create_location_agent, parse_location_response
    from agents.outage_agent import create_outage_agent
    from agents.diagnosis_agent import create_diagnosis_agent
    from agents.escalation_agent import run_escalation_pipeline
    from agentscope.message import Msg

    async def event_stream():
        try:
            # ── Stage 1: Location ──────────────────────────────────────────
            yield f"data: {json.dumps({'stage': 'location', 'status': 'thinking', 'message': 'Extracting your location...'})}\n\n"
            await asyncio.sleep(0)  # allow flush

            location_agent = create_location_agent()
            user_msg = Msg("user", message, "user")
            location_response = await location_agent(user_msg)
            location = parse_location_response(location_response)
            detected_area = location.get("area", area or "Bangalore")

            yield f"data: {json.dumps({'stage': 'location', 'status': 'done', 'result': location, 'message': f'Location identified: {detected_area}'})}\n\n"

            # ── Stage 2: Outage lookup ─────────────────────────────────────
            yield f"data: {json.dumps({'stage': 'outage', 'status': 'thinking', 'message': f'Checking outage data for {detected_area}...'})}\n\n"
            await asyncio.sleep(0)

            outage_agent = create_outage_agent()
            outage_prompt = Msg(
                "user",
                (
                    f"The user is located in: {detected_area} (Bangalore).\n"
                    f"User's original message: \"{message}\"\n\n"
                    f"Please investigate all data sources for outage information "
                    f"in {detected_area} and provide a comprehensive analysis."
                ),
                "user",
            )
            outage_response = await outage_agent(outage_prompt)
            outage_analysis = (
                outage_response.content
                if hasattr(outage_response, "content")
                else str(outage_response)
            )

            if isinstance(outage_analysis, list):
                outage_analysis_str = " ".join(str(p) for p in outage_analysis)
            else:
                outage_analysis_str = str(outage_analysis)

            outage_found = any(
                kw in outage_analysis_str.lower()
                for kw in ["active outage", "outage found", "outages_found\": 1",
                           "outages_found\": 2", "outages_found\": 3"]
            )

            yield f"data: {json.dumps({'stage': 'outage', 'status': 'done', 'result': {'outage_found': outage_found, 'area': detected_area}, 'message': 'Outage detected' if outage_found else 'No official outage found'})}\n\n"

            # ── Stage 3: Diagnosis ────────────────────────────────────────
            yield f"data: {json.dumps({'stage': 'diagnosis', 'status': 'thinking', 'message': 'Generating diagnosis and advice...'})}\n\n"
            await asyncio.sleep(0)

            diagnosis_agent = create_diagnosis_agent()
            diagnosis_prompt = Msg(
                "user",
                (
                    f"USER AREA: {detected_area}\n"
                    f"USER MESSAGE: {message}\n\n"
                    f"=== OUTAGE AGENT ANALYSIS ===\n"
                    f"{outage_analysis_str}\n\n"
                    f"Based on all the above information, generate the final "
                    f"voice response for the user."
                ),
                "user",
            )
            diagnosis_response = await diagnosis_agent(diagnosis_prompt)
            response_text = (
                diagnosis_response.content
                if hasattr(diagnosis_response, "content")
                else str(diagnosis_response)
            )
            if isinstance(response_text, list):
                response_text = " ".join(str(p) for p in response_text)

            if outage_found:
                diagnosis_type = "area_outage"
            elif "crowd" in outage_analysis_str.lower():
                diagnosis_type = "crowd_reported"
            else:
                diagnosis_type = "building_issue"

            yield f"data: {json.dumps({'stage': 'diagnosis', 'status': 'done', 'result': {'response': str(response_text), 'diagnosis_type': diagnosis_type, 'outage_found': outage_found, 'area': detected_area}, 'message': 'Diagnosis complete'})}\n\n"

            # ── Stage 4: Escalation ───────────────────────────────────────
            yield f"data: {json.dumps({'stage': 'escalation', 'status': 'thinking', 'message': 'Checking if hardware fault needs escalation...'})}\n\n"
            await asyncio.sleep(0)

            complaint = {
                "id": None,
                "complaint_id": "CHAT-STREAM",
                "text": message,
                "area": detected_area,
                "latitude": lat,
                "longitude": lon,
                "source": "chat",
            }
            esc_result = await run_escalation_pipeline(complaint)

            if esc_result.get("escalated"):
                yield f"data: {json.dumps({'stage': 'escalation', 'status': 'done', 'result': esc_result, 'message': esc_result.get('message', 'Escalated to lineman')})}\n\n"
            else:
                yield f"data: {json.dumps({'stage': 'escalation', 'status': 'skipped', 'message': 'No hardware fault — escalation not needed'})}\n\n"

            # ── Final ─────────────────────────────────────────────────────
            # Log to DB (fire and forget)
            try:
                from database.supabase_client import log_call
                log_call({
                    "caller_area": detected_area,
                    "user_message": message,
                    "ai_response": str(response_text)[:2000],
                    "outage_found": outage_found,
                    "diagnosis_type": diagnosis_type,
                })
            except Exception:
                pass

            yield f"data: {json.dumps({'stage': 'complete', 'status': 'done', 'message': 'Pipeline complete'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'stage': 'error', 'status': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )

