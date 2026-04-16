"""
Twitter/X BESCOM Scraper — RapidAPI + LangGraph + APScheduler.

Uses RapidAPI (Twttr API / Twitter154 / etc) to scrape tweets
mentioning @NammaBESCOM and search for Bangalore power outage complaints.

Environment variables (.env):
    RAPIDAPI_KEY            Your RapidAPI key
    RAPIDAPI_HOST           e.g. twttr.p.rapidapi.com or twitter154.p.rapidapi.com
    GROQ_API_KEY            Groq API key for Llama-3 (area extraction)
    TWITTER_POLL_MINUTES    Polling interval in minutes (default 15)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict

import httpx
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END

load_dotenv()

logger = logging.getLogger("vidyutseva.twitter")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OUTAGE_KEYWORDS = [
    "power cut", "power outage", "no power", "no electricity",
    "no light", "light cut", "current cut", "load shedding",
    "blackout", "bescom", "vidyut", "bijli", "current nahi",
    "power gone", "power issue", "electricity issue", "power back",
    "transformer", "maintenance", "scheduled outage",
]

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

SEARCH_QUERY = "(to:NammaBESCOM OR @NammaBESCOM) (power OR cut OR electricity)"
_STATE_FILE = Path(__file__).parent / ".twitter_rapidapi_state.json"

# ---------------------------------------------------------------------------
# LangGraph state
# ---------------------------------------------------------------------------

class TwitterPollerState(TypedDict, total=False):
    raw_tweets: list[dict]
    outage_tweets: list[dict]
    parsed_reports: list[dict]
    new_reports_count: int
    error: str | None


# ---------------------------------------------------------------------------
# Node 1: Fetch tweets via RapidAPI
# ---------------------------------------------------------------------------

def fetch_tweets_node(state: TwitterPollerState) -> TwitterPollerState:
    try:
        tweets = asyncio.run(_fetch_tweets_rapidapi())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        tweets = loop.run_until_complete(_fetch_tweets_rapidapi())
        loop.close()

    logger.info(f"[RapidAPI] Fetched {len(tweets)} total tweets")
    return {**state, "raw_tweets": tweets, "error": None}


async def _fetch_tweets_rapidapi() -> list[dict]:
    rapid_key = os.getenv("RAPIDAPI_KEY", "")
    rapid_host = os.getenv("RAPIDAPI_HOST")

    if not rapid_key or rapid_key.startswith("your_"):
        logger.warning("[RapidAPI] RAPIDAPI_KEY not set. Scraping disabled.")
        return []

    # Specifically using twitter241's /search endpoint to find citizen complaints
    endpoint = f"https://{rapid_host}/search"
    params = {"query": SEARCH_QUERY, "type": "Latest", "count": 20} 

    all_tweets: list[dict] = []
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                endpoint,
                headers={
                    "X-RapidAPI-Key": rapid_key,
                    "X-RapidAPI-Host": rapid_host
                },
                params=params,
                timeout=15.0
            )

            if res.status_code != 200:
                logger.error(f"[RapidAPI] Failed: HTTP {res.status_code} - {res.text}")
                return []

            data = res.json()
            
            # The structure for twitter241 /user-tweets is deeply nested from twitter's GraphQL
            instructions = data.get("result", {}).get("timeline", {}).get("instructions", [])
            entries = []
            for instr in instructions:
                if instr.get("type") == "TimelineAddEntries":
                    entries.extend(instr.get("entries", []))
                elif "entries" in instr:
                     entries.extend(instr.get("entries", []))

            last_state = _load_state()
            since_id = last_state.get("last_tweet_id")
            newest_id = None

            for entry in entries:
                try:
                    # deeply nested lookup
                    tweet_result = entry.get("content", {}).get("itemContent", {}).get("tweet_results", {}).get("result", {})
                    if not tweet_result:
                        continue
                    
                    legacy = tweet_result.get("legacy", {})
                    core = tweet_result.get("core", {}).get("user_results", {}).get("result", {})
                    core_legacy = core.get("legacy", {})

                    tid = tweet_result.get("rest_id") or legacy.get("id_str")
                    if not tid:
                        continue

                    if since_id and tid <= since_id:
                        continue

                    if newest_id is None or tid > newest_id:
                        newest_id = tid

                    author_name = core_legacy.get("screen_name") or core.get("screen_name") or "unknown"
                    author_id = core.get("rest_id") or "unknown"
                    
                    text = legacy.get("full_text") or legacy.get("text", "")
                    created_at = legacy.get("created_at") or datetime.now(timezone.utc).isoformat()

                    all_tweets.append({
                        "id": tid,
                        "text": text,
                        "author_id": author_id,
                        "author_name": author_name,
                        "created_at": created_at,
                        "source": "rapidapi-twitter241"
                    })
                except Exception as e:
                    logger.debug(f"[RapidAPI] skipped an entry parsing error: {e}")

            if newest_id:
                _save_state({"last_tweet_id": newest_id})

    except Exception as exc:
        logger.error(f"[RapidAPI] Fetch error: {exc}")

    return all_tweets


# ---------------------------------------------------------------------------
# Node 2: Filter to outage-relevant tweets
# ---------------------------------------------------------------------------

def filter_outage_tweets_node(state: TwitterPollerState) -> TwitterPollerState:
    raw = state.get("raw_tweets", [])
    filtered = [
        t for t in raw
        if any(kw in t.get("text", "").lower() for kw in OUTAGE_KEYWORDS)
    ]
    logger.info(f"[Filter] {len(filtered)}/{len(raw)} tweets are outage-related")
    return {**state, "outage_tweets": filtered}


# ---------------------------------------------------------------------------
# Node 3: Groq LLM area + severity extraction
# ---------------------------------------------------------------------------

def parse_with_groq_node(state: TwitterPollerState) -> TwitterPollerState:
    tweets = state.get("outage_tweets", [])
    if not tweets:
        return {**state, "parsed_reports": []}

    from database.supabase_client import get_areas
    valid_areas = [a["name"] for a in get_areas()]
    valid_areas_str = ", ".join(valid_areas)

    groq_key = os.getenv("GROQ_API_KEY", "")
    parsed = []

    for tweet in tweets:
        area, sub_area, severity = _extract_area_groq(tweet.get("text", ""), groq_key, valid_areas_str)
        parsed.append({**tweet, "area_name": area, "sub_area": sub_area, "severity": severity})

    logger.info(f"[Groq] Parsed {len(parsed)} reports")
    return {**state, "parsed_reports": parsed}


# ---------------------------------------------------------------------------
# Node 4: Store to Supabase + Qdrant via orchestrator
# ---------------------------------------------------------------------------

def store_reports_node(state: TwitterPollerState) -> TwitterPollerState:
    reports = state.get("parsed_reports", [])
    if not reports:
        return {**state, "new_reports_count": 0}

    from agents.orchestrator import get_orchestrator
    orchestrator = get_orchestrator()
    stored = 0

    for report in reports:
        area = report["area_name"]
        sub_area = report.get("sub_area", "")
        if not area or area.lower() == "unknown":
            continue

        prefix = f"[X/@{report['author_name']}] "
        if sub_area and sub_area.lower() != "unknown":
            prefix += f"Location: {sub_area} | "
            
        description = f"{prefix}{report['text']} (Tweet ID: {report['id']})"
        try:
            result = asyncio.run(
                orchestrator.submit_crowd_report(
                    area_name=area,
                    description=description,
                    reporter_phone=None,
                    report_source="rapidapi",
                )
            )
            stored += 1
            logger.info(f"[Store] '{area}' -> auto_outage={result.get('auto_outage_created')}")
        except Exception as exc:
            logger.error(f"[Store] Failed for tweet {report['id']}: {exc}")

    return {**state, "new_reports_count": stored}


# ---------------------------------------------------------------------------
# Build LangGraph
# ---------------------------------------------------------------------------

_graph = None

def _build_graph():
    g = StateGraph(TwitterPollerState)
    g.add_node("fetch_tweets", fetch_tweets_node)
    g.add_node("filter_outage_tweets", filter_outage_tweets_node)
    g.add_node("parse_with_groq", parse_with_groq_node)
    g.add_node("store_reports", store_reports_node)

    g.set_entry_point("fetch_tweets")
    g.add_edge("fetch_tweets", "filter_outage_tweets")
    g.add_edge("filter_outage_tweets", "parse_with_groq")
    g.add_edge("parse_with_groq", "store_reports")
    g.add_edge("store_reports", END)

    return g.compile()

def get_twitter_graph():
    global _graph
    if _graph is None:
        _graph = _build_graph()
    return _graph

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_twitter_poll():
    logger.info("[RapidAPI] Starting poll cycle...")
    try:
        initial: TwitterPollerState = {"raw_tweets": [], "outage_tweets": [], "parsed_reports": [], "new_reports_count": 0, "error": None}
        result = get_twitter_graph().invoke(initial)
        logger.info(f"[RapidAPI] Done — fetched={len(result.get('raw_tweets', []))} stored={result.get('new_reports_count', 0)}")
    except Exception as exc:
        logger.error(f"[RapidAPI] Poll failed: {exc}", exc_info=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_area_groq(text: str, groq_key: str, valid_areas: str = "") -> tuple[str, str, int]:
    if groq_key and not groq_key.startswith("your_"):
        try:
            prompt = (
                f"You are a location extractor for Bangalore, India.\\n"
                f"Given a tweet about an electricity issue, extract:\\n"
                f"1. The neighborhood (MUST be one from this list: {valid_areas})\\n"
                f"2. A more specific sub-area or landmark if mentioned (like '5th cross' or 'EWS Colony')\\n"
                f"3. Severity: 1=minor, 2=moderate, 3=major\\n\\n"
                f"Tweet: \\\"{text}\\\"\\n\\n"
                f"Respond ONLY with JSON: {{\"area_name\": \"<neighborhood>\", \"sub_area\": \"<landmark or unknown>\", \"severity\": <1|2|3>}}"
            )
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0,
                        "response_format": {"type": "json_object"},
                    },
                )
                resp.raise_for_status()
                parsed = json.loads(resp.json()["choices"][0]["message"]["content"])
                return parsed.get("area_name", "unknown"), parsed.get("sub_area", "unknown"), int(parsed.get("severity", 1))
        except Exception:
            pass

    text_lower = text.lower()
    for area in BANGALORE_AREAS:
        if area.lower() in text_lower:
            return area, "unknown", 1
    return "unknown", "unknown", 1


def _load_state() -> dict:
    return json.loads(_STATE_FILE.read_text()) if _STATE_FILE.exists() else {}

def _save_state(data: dict) -> None:
    try:
        existing = _load_state()
        existing.update(data)
        _STATE_FILE.write_text(json.dumps(existing))
    except Exception:
        pass
