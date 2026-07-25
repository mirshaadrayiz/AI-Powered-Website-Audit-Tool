import asyncio

from app.llm.prompts import SYSTEM_PROMPT
from app.schemas import AIAnalysisSchema
from app.scraper.scrape import ScrapedPage
from app.web_audit_tool import audit_website


def test_audit_website_combines_scraper_facts_with_ai_analysis(monkeypatch, make_metrics, make_analysis):
    metrics = make_metrics(total_word_count=999)
    scraped = ScrapedPage(metrics=metrics, content="Some visible page text.")
    analysis = make_analysis()

    captured = {}

    async def fake_scrape_page(url):
        captured["scrape_url"] = url
        return scraped

    async def fake_generate_structured(system_prompt, user_prompt, schema):
        captured["system_prompt"] = system_prompt
        captured["user_prompt"] = user_prompt
        captured["schema"] = schema
        return "raw json", analysis

    monkeypatch.setattr("app.web_audit_tool.scrape_page", fake_scrape_page)
    monkeypatch.setattr("app.web_audit_tool.generate_structured", fake_generate_structured)

    result = asyncio.run(audit_website("https://example.com/page"))

    assert captured["scrape_url"] == "https://example.com/page"
    assert captured["system_prompt"] == SYSTEM_PROMPT
    assert captured["schema"] is AIAnalysisSchema
    assert "Some visible page text." in captured["user_prompt"]

    # Facts must come from the scraper, never from the model.
    assert result.factual_metrics == metrics

    # Insights/recommendations must come straight from the AI analysis.
    assert result.insights == analysis.insights
    assert result.recommendations == analysis.recommendations
