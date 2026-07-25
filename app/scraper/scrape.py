from dataclasses import dataclass

from app.schemas import FactualMetricsSchema
from app.scraper.fetch import fetch_html
from app.scraper.metrics import extract_metrics
from app.scraper.parser import extract_visible_text, parse_html


@dataclass
class ScrapedPage:
    """Internal handoff between the scraper and the AI layer.

    Not a schemas.py model on purpose — FactualMetricsSchema/OutputSchema
    are the validated external API contract; this is just a plain internal
    transport object, so a dataclass is enough.
    """

    metrics: FactualMetricsSchema
    content: str


async def scrape_page(url: str) -> ScrapedPage:
    """Fetch and parse a URL into factual metrics + page content.

    The single entry point into the scraper subsystem — callers only need
    this function, not the individual fetch/parse/metrics pieces.
    """
    html = await fetch_html(url)
    soup = parse_html(html)

    return ScrapedPage(
        metrics=extract_metrics(soup, url),
        content=extract_visible_text(soup),
    )

if __name__ == "__main__":

    """ uv run -m app.scraper.scrape """
 
    import asyncio
    import sys

    url = "https://learn.deeplearning.ai/courses/a2a-the-agent2agent-protocol/lesson/vtf72ap4/introduction"

    try:
        scraped_page = asyncio.run(scrape_page(url))
        print("Metrics:")
        print(scraped_page.metrics.model_dump_json(indent=2))
        # print("Content:", scraped_page.content)
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        sys.exit(1)