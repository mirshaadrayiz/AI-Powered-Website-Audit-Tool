import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app.llm.client import AIError
from app.schemas import InputSchema, OutputSchema
from app.scraper.fetch import FetchError
from app.web_audit_tool import audit_website

logging.basicConfig(level=logging.INFO)

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="AI-Powered Website Audit Tool",
    description=(
        "Extracts factual metrics from a single webpage and generates "
        "AI-grounded insights and prioritized recommendations."
    ),
)


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    """Serve the web app's single page."""
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/audit")
async def audit(input_data: InputSchema) -> OutputSchema:
    """Scrape and audit a single page, returning factual metrics plus AI insights."""
    try:
        return await audit_website(str(input_data.url))
    except FetchError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except AIError as e:
        raise HTTPException(status_code=502, detail=f"AI provider error: {e}")
