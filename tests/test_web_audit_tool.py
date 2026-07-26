import asyncio

from app.llm.prompts import SYSTEM_PROMPT
from app.schemas import AIAnalysisSchema, HeadingCountsSchema, InsightDetailSchema, InsightSchema
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


def test_audit_website_keeps_an_accurate_list_valued_citation(monkeypatch, make_metrics, make_recommendations):
    metrics = make_metrics(
        heading_counts=HeadingCountsSchema(h1_count=1, h2_count=1, h3_count=0, sequence=["h1", "h2"])
    )
    scraped = ScrapedPage(metrics=metrics, content="Some visible page text.")

    def detail(cited):
        return InsightDetailSchema(analysis="x", metrics_cited=cited)

    accurate_citation = 'heading_counts.sequence: ["h1", "h2"]'
    insights = InsightSchema(
        seo_structure=detail([accurate_citation]),
        messaging_clarity=detail(["total_word_count: 263"]),
        cta_usage=detail(["total_word_count: 263"]),
        content_depth=detail(["total_word_count: 263"]),
        ux_concerns=detail(["total_word_count: 263"]),
        structural_concerns=detail(["total_word_count: 263"]),
    )
    analysis = AIAnalysisSchema(insights=insights, recommendations=make_recommendations())

    async def fake_scrape_page(url):
        return scraped

    async def fake_generate_structured(system_prompt, user_prompt, schema):
        return "raw json", analysis

    monkeypatch.setattr("app.web_audit_tool.scrape_page", fake_scrape_page)
    monkeypatch.setattr("app.web_audit_tool.generate_structured", fake_generate_structured)

    result = asyncio.run(audit_website("https://example.com/page"))

    # A list-valued citation that exactly matches the real value (in the JSON
    # form the model actually read) must not be flagged as unverified.
    assert result.insights.seo_structure.metrics_cited == [accurate_citation]


def test_audit_website_verifies_quoted_string_citations_and_still_catches_wrong_ones(
    monkeypatch, make_metrics, make_recommendations
):
    """Strings reach the model quoted, and a curly quote reaches it literally."""
    metrics = make_metrics(
        total_word_count=263,
        meta_title="Nanotek.lk | Computer Store",
        meta_description="Sri Lanka’s largest range — islandwide delivery.",
    )
    scraped = ScrapedPage(metrics=metrics, content="Some visible page text.")

    def detail(cited):
        return InsightDetailSchema(analysis="x", metrics_cited=cited)

    cited = [
        'meta_title: "Nanotek.lk | Computer Store"',
        "meta_title: Nanotek.lk | Computer Store",
        'meta_description: "Sri Lanka’s largest range — islandwide delivery."',
        "total_word_count: 999",
    ]
    insights = InsightSchema(
        seo_structure=detail(cited),
        messaging_clarity=detail(["total_word_count: 263"]),
        cta_usage=detail(["total_word_count: 263"]),
        content_depth=detail(["total_word_count: 263"]),
        ux_concerns=detail(["total_word_count: 263"]),
        structural_concerns=detail(["total_word_count: 263"]),
    )
    analysis = AIAnalysisSchema(insights=insights, recommendations=make_recommendations())

    async def fake_scrape_page(url):
        return scraped

    async def fake_generate_structured(system_prompt, user_prompt, schema):
        return "raw json", analysis

    monkeypatch.setattr("app.web_audit_tool.scrape_page", fake_scrape_page)
    monkeypatch.setattr("app.web_audit_tool.generate_structured", fake_generate_structured)

    result = asyncio.run(audit_website("https://example.com/page"))

    assert result.insights.seo_structure.metrics_cited == cited[:3] + [
        "total_word_count: 999 (unverified)"
    ]
