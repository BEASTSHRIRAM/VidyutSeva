"""
BESCOM outage scraper powered by Firecrawl.
Uses structured JSON extraction to pull outage data from BESCOM's planned outages page.
"""

import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from firecrawl import Firecrawl

load_dotenv()


# ---------------------------------------------------------------------------
# Schema for structured extraction
# ---------------------------------------------------------------------------

class BESCOMOutageItem(BaseModel):
    """Single outage record extracted from BESCOM page."""
    area_name: str = Field(description="Area or locality name in Bangalore")
    outage_type: str = Field(
        default="planned_maintenance",
        description="Type: planned_maintenance, emergency, or load_shedding",
    )
    reason: str = Field(default="", description="Reason for the outage")
    start_time: str = Field(default="", description="Outage start time as ISO string")
    end_time: str = Field(default="", description="Outage end time as ISO string or empty")
    affected_areas: list[str] = Field(
        default_factory=list,
        description="List of specific sub-areas or roads affected",
    )


class BESCOMOutageResponse(BaseModel):
    """Wrapper for multiple extracted outages."""
    outages: list[BESCOMOutageItem] = Field(default_factory=list)
    page_title: str = Field(default="")
    last_updated: str = Field(default="")


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------

class BESCOMScraper:
    """Firecrawl-based BESCOM outage scraper."""

    def __init__(self):
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key or api_key.startswith("your_"):
            raise RuntimeError("FIRECRAWL_API_KEY must be set in .env")
        self.firecrawl = Firecrawl(api_key=api_key)
        self.bescom_url = os.getenv(
            "BESCOM_OUTAGE_URL",
            "https://bescom.karnataka.gov.in/new-page/Planned%20Outages%20-%20BESCOM%20Works",
        )

    def scrape_outages(self) -> list[dict]:
        """
        Scrape BESCOM planned outage page and return structured outage data.
        Uses Firecrawl's JSON extraction with a Pydantic schema.
        """
        try:
            result = self.firecrawl.scrape(
                self.bescom_url,
                formats=[
                    {
                        "type": "json",
                        "schema": BESCOMOutageResponse.model_json_schema(),
                    }
                ],
                only_main_content=True,
                timeout=120000,
            )

            # Also get markdown for RAG embedding
            md_result = self.firecrawl.scrape(
                self.bescom_url,
                formats=["markdown"],
                only_main_content=True,
                timeout=60000,
            )

            outages = []
            json_data = result.get("json", {}) if isinstance(result, dict) else {}

            if isinstance(json_data, dict) and "outages" in json_data:
                for item in json_data["outages"]:
                    outages.append(
                        {
                            "area_name": item.get("area_name", "Unknown"),
                            "outage_type": item.get("outage_type", "planned_maintenance"),
                            "reason": item.get("reason", ""),
                            "start_time": item.get("start_time", datetime.now(timezone.utc).isoformat()),
                            "end_time": item.get("end_time"),
                            "status": "scheduled",
                            "source": "bescom_scraper",
                            "affected_areas": item.get("affected_areas", []),
                            "severity": 2,
                        }
                    )

            # Return outages + raw markdown for knowledge embedding
            markdown = ""
            if isinstance(md_result, dict):
                markdown = md_result.get("markdown", "")

            return outages, markdown

        except Exception as e:
            print(f"[BESCOMScraper] Error scraping: {e}")
            return [], ""

    def scrape_and_store(self) -> dict:
        """
        Full pipeline: scrape → upsert to Supabase → embed in Qdrant.
        Returns summary of what was stored.
        """
        from database.supabase_client import create_outage, get_active_outages
        from qdrant.vector_store import embed_outage, embed_knowledge

        outages, markdown = self.scrape_outages()

        stored = 0
        skipped = 0

        for outage_data in outages:
            # Check for duplicates (same area + same day)
            existing = get_active_outages(outage_data["area_name"])
            if existing:
                skipped += 1
                continue

            # Store in Supabase
            record = create_outage(outage_data)
            if record:
                # Embed in Qdrant
                embed_outage(record)
                stored += 1

        # Embed raw markdown as knowledge chunks
        knowledge_chunks = 0
        if markdown:
            # Split into ~500 char chunks for RAG
            chunks = _split_text(markdown, chunk_size=500, overlap=50)
            for chunk in chunks:
                embed_knowledge(
                    chunk,
                    metadata={
                        "source": "bescom_scraper",
                        "url": self.bescom_url,
                        "scraped_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
                knowledge_chunks += 1

        return {
            "outages_found": len(outages),
            "outages_stored": stored,
            "outages_skipped": skipped,
            "knowledge_chunks": knowledge_chunks,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }


def _split_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return [c.strip() for c in chunks if c.strip()]
