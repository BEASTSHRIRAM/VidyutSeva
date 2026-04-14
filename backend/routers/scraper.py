"""
Scraper trigger routes.
"""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/scraper", tags=["scraper"])


@router.post("/run")
async def run_scraper():
    """Manually trigger BESCOM outage scraper."""
    try:
        from scraper.bescom_scraper import BESCOMScraper
        scraper = BESCOMScraper()
        result = scraper.scrape_and_store()
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Scraper failed: {e}",
        )
