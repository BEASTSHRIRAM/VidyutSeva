"""
VidyutSeva — FastAPI Backend Entry Point
AI-powered electricity support for Bangalore citizens.
"""

import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

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

    # Optional: start background scraper scheduler
    try:
        interval = int(os.getenv("SCRAPER_INTERVAL_HOURS", "3"))
        if interval > 0 and not os.getenv("FIRECRAWL_API_KEY", "").startswith("your_"):
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            scheduler = AsyncIOScheduler()

            def scrape_job():
                try:
                    from scraper.bescom_scraper import BESCOMScraper
                    scraper = BESCOMScraper()
                    result = scraper.scrape_and_store()
                    print(f"[Scheduler] Scrape complete: {result}")
                except Exception as exc:
                    print(f"[Scheduler] Scrape failed: {exc}")

            scheduler.add_job(scrape_job, "interval", hours=interval)
            scheduler.start()
            print(f"✅ Background scraper scheduled every {interval}h")
    except Exception as e:
        print(f"⚠️  Scheduler skipped: {e}")

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
    allow_headers=["*"],
)

# Register routers
from routers.outages import router as outages_router
from routers.dashboard import router as dashboard_router
from routers.scraper import router as scraper_router
from routers.crowd_reports import router as reports_router
from routers.alerts import router as alerts_router
from voice.vapi_handler import router as voice_router

app.include_router(outages_router)
app.include_router(dashboard_router)
app.include_router(scraper_router)
app.include_router(reports_router)
app.include_router(alerts_router)
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
