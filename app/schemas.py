from typing import List
from pydantic import BaseModel, Field, HttpUrl

class InputSchema(BaseModel):

    """
        Input schema for the API endpoint.
    """

    url: HttpUrl = Field(..., description="The URL of the page to analyze.")


class HeadingCountsSchema(BaseModel):

    """
        Schema for heading counts.
    """

    h1_count: int = Field(..., description="Total number of H1 headings in the text.")
    h2_count: int = Field(..., description="Total number of H2 headings in the text.")
    h3_count: int = Field(..., description="Total number of H3 headings in the text.")


class FactualMetricsSchema(BaseModel):

    """
        Schema for factual metrics.
    """

    total_word_count: int = Field(..., description="Total number of words in the text.")
    heading_counts: HeadingCountsSchema = Field(..., description="Counts of different heading levels in the text.")
    ctas_count: int = Field(..., description="Total number of Call-To-Actions (CTAs) in the text.")
    internal_links_count: int = Field(..., description="Total number of internal links in the text.")
    external_links_count: int = Field(..., description="Total number of external links in the text.")
    image_count: int = Field(..., description="Total number of images in the text.")
    image_missing_alttext_percent: int = Field(..., description="Percentage of images missing alt text in the text.")
    meta_title: str = Field(..., description="The meta title of the page.")
    meta_description: str = Field(..., description="The meta description of the page.")


class InsightSchema(BaseModel):

    """
        Schema for insights.
        These insights are generated from the factual metrics and provide a deep analysis.
    """

    seo_structure: str = Field(..., description="Insights related to the SEO structure of the page.")
    messaging_clarity: str = Field(..., description="Insights related to the clarity of messaging on the page.")
    cta_usage: str = Field(..., description="Insights related to the usage of Call-To-Actions (CTAs) on the page.")
    content_depth: str = Field(..., description="Insights related to the depth of content on the page.")
    ux_concerns: str = Field(..., description="Insights related to user experience (UX) concerns on the page.")
    structural_concerns: str = Field(..., description="Insights related to structural concerns on the page.")


class RecommendationReasoningSchema(BaseModel):

    """
        Schema for recommendations.
        These recommendations are generated based on the insights and provide actionable steps.
    """

    recommendation: str = Field(..., description="The recommendation provided based on the insights.")
    reasoning: str = Field(..., description="The reasoning behind the recommendation.")

class RecommendationSchema(BaseModel):

    """
        Schema for recommendations.
        These recommendations are generated based on the insights and provide actionable steps.
    """

    recommendation: List[RecommendationReasoningSchema] = Field(..., description="List of recommendations with reasoning.")




class OutputSchema(BaseModel):

    """
        Output schema for the API endpoint.
    """

    factual_metrics: FactualMetricsSchema = Field(..., description="Factual metrics extracted from the text.")
    insights: InsightSchema = Field(..., description="Insights generated from the factual metrics.")
    recommendations: RecommendationSchema = Field(..., description="Recommendations generated based on the insights.")
