from pydantic import BaseModel, Field, HttpUrl, computed_field


class InputSchema(BaseModel):
    """Input schema for the API endpoint."""

    url: HttpUrl = Field(..., description="The URL of the page to analyze.")


class HeadingCountsSchema(BaseModel):
    """Schema for heading counts."""

    h1_count: int = Field(..., description="Total number of H1 headings in the text.")
    h2_count: int = Field(..., description="Total number of H2 headings in the text.")
    h3_count: int = Field(..., description="Total number of H3 headings in the text.")
    sequence: list[str] = Field(
        ...,
        description=(
            "H1-H3 tag names in document order (e.g. ['h1', 'h2', 'h2', 'h3']). "
            "Reveals hierarchy jumps (e.g. H1 straight to H3) that raw counts alone cannot."
        ),
    )


class FactualMetricsSchema(BaseModel):
    """Schema for factual metrics."""

    total_word_count: int = Field(..., description="Total number of words in the text.")
    heading_counts: HeadingCountsSchema = Field(..., description="Counts of different heading levels in the text.")
    ctas_count: int = Field(..., description="Total number of Call-To-Actions (CTAs) in the text.")
    internal_links_count: int = Field(..., description="Total number of internal link instances in the text.")
    external_links_count: int = Field(..., description="Total number of external link instances in the text.")
    unique_internal_links_count: int = Field(..., description="Number of distinct internal link destinations — repeats to the same URL count once.")
    unique_external_links_count: int = Field(..., description="Number of distinct external link destinations — repeats to the same URL count once.")
    image_count: int = Field(..., description="Total number of images in the text.")
    image_missing_alt_count: int = Field(..., description="Number of images with no alt attribute at all — a real accessibility gap.")
    image_decorative_alt_count: int = Field(..., description='Number of images with alt="" (empty but present).')

    @computed_field(description="Percentage of images with no alt attribute at all (0 if there are no images).")
    @property
    def image_missing_alt_percent(self) -> float:
        if self.image_count == 0:
            return 0.0
        return round(self.image_missing_alt_count / self.image_count * 100, 1)

    meta_title: str = Field(..., description="The meta title of the page.")
    meta_title_length: int = Field(..., description="Character count of the meta title.")
    meta_description: str = Field(..., description="The meta description of the page.")
    meta_description_length: int = Field(..., description="Character count of the meta description.")


class InsightDetailSchema(BaseModel):
    """One insight dimension: the analysis, plus the factual data it references.

    The two are separate fields rather than one blob of prose because
    we require insights to be grounded in the extracted metrics and to
    clearly reference the factual data.
    """

    analysis: str = Field(..., description="The insight itself, a few sentences.")
    metrics_cited: list[str] = Field(
        ...,
        min_length=1,
        description=(
            "FactualMetricsSchema field(s) this insight is grounded in, as "
            "field_name: value copied exactly from the metrics block"
        ),
    )


class InsightSchema(BaseModel):
    """Schema for insights.

    These insights are generated from the factual metrics and provide a deep analysis.
    """

    seo_structure: InsightDetailSchema = Field(..., description="Insights related to the SEO structure of the page.")
    messaging_clarity: InsightDetailSchema = Field(..., description="Insights related to the clarity of messaging on the page.")
    cta_usage: InsightDetailSchema = Field(..., description="Insights related to the usage of Call-To-Actions (CTAs) on the page.")
    content_depth: InsightDetailSchema = Field(..., description="Insights related to the depth of content on the page.")
    ux_concerns: InsightDetailSchema = Field(..., description="Insights related to user experience (UX) concerns on the page.")
    structural_concerns: InsightDetailSchema = Field(..., description="Insights related to structural concerns on the page.")


class RecommendationReasoningSchema(BaseModel):
    """Schema for a single recommendation.

    Generated from the insights and provides an actionable step plus its reasoning.
    """

    recommendation: str = Field(..., description="The recommendation provided based on the insights.")
    reasoning: str = Field(
        ..., description="Why this action follows, citing the specific metric value(s) behind it"
    )


class AIAnalysisSchema(BaseModel):
    """The shape of a single AI call's output: insights + recommendations only.

    Not factual_metrics — those come from the scraper, never the model. This
    is what gets forced as the model's structured output schema.
    """

    insights: InsightSchema = Field(..., description="Insights generated from the factual metrics.")
    recommendations: list[RecommendationReasoningSchema] = Field(
        ...,
        min_length=3,
        max_length=5,
        description="3 to 5 prioritized, actionable recommendations with reasoning, most impactful first.",
    )


class OutputSchema(BaseModel):
    """The shape of the API's output: factual metrics + AI analysis.

    This is what the API returns to the caller, combining both halves.
    """

    factual_metrics: FactualMetricsSchema = Field(..., description="Factual metrics extracted from the page.")
    insights: InsightSchema = Field(..., description="Insights generated from the factual metrics.")
    recommendations: list[RecommendationReasoningSchema] = Field(
        ...,
        min_length=3,
        max_length=5,
        description="3 to 5 prioritized, actionable recommendations with reasoning, most impactful first.",
    )
