from dataclasses import dataclass

from app.schemas import FactualMetricsSchema
from app.scraper.fetch import fetch_html
from app.scraper.metrics import extract_metrics
from app.scraper.parser import parse_html, strip_chrome, text_from_scope


@dataclass
class ScrapedPage:
    """Internal handoff between the scraper and the AI layer.

    FactualMetricsSchema/OutputSchema are the validated external API contract;
    this is just a plain internal transport object, so a dataclass is enough.
    """

    metrics: FactualMetricsSchema
    content: str


async def scrape_page(url: str) -> ScrapedPage:
    """Fetch and parse a URL into factual metrics + page content.

    The single entry point into the scraper subsystem — callers only need
    this function, not the individual fetch/parse/metrics pieces. Scopes the
    page to its real content once (see strip_chrome) and reuses that scope
    for both metrics and content, rather than re-deriving it per output.
    """
    html = await fetch_html(url)
    soup = parse_html(html)
    content_soup = strip_chrome(soup)

    return ScrapedPage(
        metrics=extract_metrics(content_soup, url),
        content=text_from_scope(content_soup),
    )