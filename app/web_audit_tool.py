"""Pipeline orchestrator: scrape -> AI analysis -> combined output.

Importable as `audit_website`, and runnable standalone via
`uv run -m app.web_audit_tool <url>` (see __main__ below).
"""

import json
import logging

from app.llm.client import generate_structured
from app.llm.prompts import SYSTEM_PROMPT, build_user_prompt
from app.schemas import AIAnalysisSchema, FactualMetricsSchema, InsightSchema, OutputSchema
from app.scraper.scrape import scrape_page

logger = logging.getLogger(__name__)


def _cited_value_matches(value, claimed: str) -> bool:
    """Whether a citation's value matches the real one, in either form a model copies it.

    The metrics block in the prompt is JSON, so a list reaches the model as
    ["h1", "h2"] and a string reaches it quoted — json.dumps reproduces both,
    with ensure_ascii=False since the prompt carries literal UTF-8 (a curly
    quote in a meta title must not be compared against a \\u escape). Models
    also cite scalars bare, so str() is accepted too.
    """
    return claimed in (str(value), json.dumps(value, ensure_ascii=False))


def _verify_citations(insights: InsightSchema, metrics: FactualMetricsSchema) -> None:
    """Flag any metrics_cited entry that doesn't match the real scraped value."""
    facts = metrics.model_dump()
    for field_name in type(insights).model_fields:
        detail = getattr(insights, field_name)
        flagged = []
        for citation in detail.metrics_cited:
            field_path, _, claimed_value = citation.partition(":")
            value = facts
            for part in field_path.strip().split("."):
                value = value.get(part) if isinstance(value, dict) else None
            if value is not None and _cited_value_matches(value, claimed_value.strip()):
                flagged.append(citation)
            else:
                flagged.append(f"{citation} (unverified)")
        detail.metrics_cited = flagged


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
    _verify_citations(analysis.insights, scraped_page.metrics)

    output = OutputSchema(
        factual_metrics=scraped_page.metrics,
        insights=analysis.insights,
        recommendations=analysis.recommendations,
    )
    logger.info("Audit result for %s:\n%s", url, output.model_dump_json(indent=2))
    return output

if __name__ == "__main__":
    # uv run -m app.web_audit_tool <url>
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