import logging

from app.llm.client import generate_structured
from app.llm.prompts import SYSTEM_PROMPT, build_user_prompt
from app.schemas import AIAnalysisSchema, OutputSchema
from app.scraper.scrape import scrape_page

logger = logging.getLogger(__name__)


async def audit_website(url: str) -> OutputSchema:
    """Run the full audit pipeline for a single URL: scrape -> AI analysis -> combined output.

    factual_metrics always comes from the scraper, never the model — this
    function is the one place that assembles both halves into the final
    OutputSchema.
    """
    scraped_page = await scrape_page(url)

    user_prompt = build_user_prompt(url, scraped_page)
    _, analysis = await generate_structured(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        schema=AIAnalysisSchema,
    )

    output = OutputSchema(
        factual_metrics=scraped_page.metrics,
        insights=analysis.insights,
        recommendations=analysis.recommendations,
    )
    logger.info("Audit result for %s:\n%s", url, output.model_dump_json(indent=2))
    return output

if __name__ == "__main__":
    """ uv run -m app.web_audit_tool """

    import asyncio
    import sys

    if len(sys.argv) != 2:
        print("Usage: uv run -m app.web_audit_tool <url>")
        sys.exit(1)

    url = sys.argv[1]

    try:
        output = asyncio.run(audit_website(url))
        print(output.model_dump_json(indent=2))
    except Exception as e:
        print(f"Error auditing {url}: {e}")
        sys.exit(1)