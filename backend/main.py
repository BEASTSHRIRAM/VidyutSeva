"""
VidyutSeva — FastAPI Backend Entry Point
AI-powered electricity support for Bangalore citizens.
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

load_dotenv()

# Add backend to path for package imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialize Qdrant collections. Shutdown: cleanup."""
    print("🔌 VidyutSeva starting up...")
    try:
        from qdrant.vector_store import init_collections
        init_collections()
        print("✅ Qdrant collections initialized")
    except Exception as e:
        print(f"⚠️  Qdrant init skipped (configure QDRANT_URL in .env): {e}")

    # ── Background scheduler ──────────────────────────────────────────────
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        scheduler = AsyncIOScheduler()

        # BESCOM website scraper (every N hours)
        interval = int(os.getenv("SCRAPER_INTERVAL_HOURS", "3"))
        if interval > 0 and not os.getenv("FIRECRAWL_API_KEY", "").startswith("your_"):
            def scrape_job():
                try:
                    from scraper.bescom_scraper import BESCOMScraper
                    scraper = BESCOMScraper()
                    result = scraper.scrape_and_store()
                    print(f"[Scheduler] BESCOM scrape complete: {result}")
                except Exception as exc:
                    print(f"[Scheduler] BESCOM scrape failed: {exc}")
            scheduler.add_job(scrape_job, "interval", hours=interval, id="bescom_scraper")
            print(f"✅ BESCOM scraper scheduled every {interval}h")

        # Twitter/X mentions poller (every 15 min)
        twitter_interval = int(os.getenv("TWITTER_POLL_MINUTES", "15"))
        if os.getenv("RAPIDAPI_KEY", "") and not os.getenv("RAPIDAPI_KEY", "").startswith("your_"):
            from scraper.twitter_scraper import run_twitter_poll
            scheduler.add_job(
                run_twitter_poll,
                "interval",
                minutes=twitter_interval,
                id="twitter_poller",
                max_instances=1,        # prevent overlapping runs
            )
            # Also run once immediately on startup to backfill recent mentions
            scheduler.add_job(run_twitter_poll, "date", id="twitter_initial")
            print(f"✅ Twitter/X poller scheduled every {twitter_interval} min via RapidAPI")
        else:
            print("⚠️  Twitter poller skipped (set RAPIDAPI_KEY in .env)")

        scheduler.start()
        print("✅ Background scheduler started")
    except Exception as e:
        print(f"⚠️  Scheduler failed to start: {e}")

    yield
    print("🔌 VidyutSeva shutting down...")


app = FastAPI(
    title="VidyutSeva API",
    description="AI-powered electricity outage support for Bangalore",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "Authorization"],
)

# Register routers
from routers.outages import router as outages_router
from routers.dashboard import router as dashboard_router
from routers.scraper import router as scraper_router
from routers.crowd_reports import router as reports_router
from routers.alerts import router as alerts_router
from routers.auth import router as auth_router
from routers.complaints import router as complaints_router
from voice.vapi_handler import router as voice_router

app.include_router(outages_router)
app.include_router(dashboard_router)
app.include_router(scraper_router)
app.include_router(reports_router)
app.include_router(alerts_router)
app.include_router(auth_router)
app.include_router(complaints_router)
app.include_router(voice_router)


@app.get("/")
async def root():
    return {
        "name": "VidyutSeva API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/live-outages")
async def live_outages(
    status: str = "active",
    area: str | None = None,
    limit: int = 100,
):
    """
    Live outage feed for map dashboard.
    Returns active outages from Supabase + crowd reports matching area filter.
    Frontend polls this every 30–60 s.
    """
    from database.supabase_client import get_active_outages, get_crowd_reports

    outages = get_active_outages(area_name=area)
    crowd = get_crowd_reports(area_name=area, limit=50)

    # Serialize datetime fields
    def _serialize(row: dict) -> dict:
        return {
            k: str(v) if hasattr(v, "isoformat") else v
            for k, v in row.items()
        }

    return {
        "outages": [_serialize(o) for o in outages],
        "crowd_reports": [_serialize(r) for r in crowd],
        "total": len(outages) + len(crowd),
    }
