import os

os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("GEMINI_MODEL", "gemini-3.6-flash")

import pytest

from app.schemas import (
    AIAnalysisSchema,
    FactualMetricsSchema,
    HeadingCountsSchema,
    InsightDetailSchema,
    InsightSchema,
    OutputSchema,
    RecommendationReasoningSchema,
)


@pytest.fixture
def make_metrics():
    def _make(**overrides) -> FactualMetricsSchema:
        defaults = dict(
            total_word_count=263,
            heading_counts=HeadingCountsSchema(
                h1_count=1, h2_count=2, h3_count=0, sequence=["h1", "h2", "h2"]
            ),
            ctas_count=1,
            internal_links_count=3,
            external_links_count=1,
            unique_internal_links_count=3,
            unique_external_links_count=1,
            image_count=2,
            image_missing_alt_count=1,
            image_decorative_alt_count=1,
            meta_title="Sample",
            meta_title_length=len("Sample"),
            meta_description="A sample page.",
            meta_description_length=len("A sample page."),
        )
        defaults.update(overrides)
        return FactualMetricsSchema(**defaults)

    return _make


@pytest.fixture
def make_insights():
    def _make() -> InsightSchema:
        def detail(field: str) -> InsightDetailSchema:
            return InsightDetailSchema(
                analysis=f"Analysis grounded in {field}.", metrics_cited=[f"{field}: 1"]
            )

        return InsightSchema(
            seo_structure=detail("meta_title"),
            messaging_clarity=detail("total_word_count"),
            cta_usage=detail("ctas_count"),
            content_depth=detail("total_word_count"),
            ux_concerns=detail("image_missing_alt_count"),
            structural_concerns=detail("heading_counts.h1_count"),
        )

    return _make


@pytest.fixture
def make_recommendations():
    def _make(count: int = 3) -> list[RecommendationReasoningSchema]:
        return [
            RecommendationReasoningSchema(
                recommendation=f"Do thing {i}", reasoning=f"Because metric {i}"
            )
            for i in range(count)
        ]

    return _make


@pytest.fixture
def make_analysis(make_insights, make_recommendations):
    def _make() -> AIAnalysisSchema:
        return AIAnalysisSchema(insights=make_insights(), recommendations=make_recommendations())

    return _make


@pytest.fixture
def make_output(make_metrics, make_insights, make_recommendations):
    def _make() -> OutputSchema:
        return OutputSchema(
            factual_metrics=make_metrics(),
            insights=make_insights(),
            recommendations=make_recommendations(),
        )

    return _make
