from app.scraper.metrics import extract_metrics
from app.scraper.parser import parse_html

SOURCE_URL = "https://www.example.com/page"


def metrics_for(html: str, source_url: str = SOURCE_URL):
    return extract_metrics(parse_html(html), source_url)


def test_heading_counts():
    metrics = metrics_for("<h1>A</h1><h2>B</h2><h2>C</h2><h3>D</h3><h3>E</h3><h3>F</h3>")

    assert metrics.heading_counts.h1_count == 1
    assert metrics.heading_counts.h2_count == 2
    assert metrics.heading_counts.h3_count == 3


def test_heading_sequence_preserves_document_order_and_reveals_jumps():
    metrics = metrics_for("<h1>A</h1><h3>B</h3><h2>C</h2><h1>D</h1>")

    assert metrics.heading_counts.sequence == ["h1", "h3", "h2", "h1"]


def test_word_count_reflects_visible_text_only():
    html = """
    <script>var hidden = "not counted at all here";</script>
    <style>.a { color: red; }</style>
    <p>Five visible words here now.</p>
    """
    metrics = metrics_for(html)

    assert metrics.total_word_count == 5


def test_ctas_count_buttons_submit_inputs_and_styled_anchors_only():
    html = """
    <button>Click</button>
    <input type="submit" value="Go">
    <input type="text">
    <a href="/signup" class="btn btn-primary">Sign Up</a>
    <a href="/about">About</a>
    """
    metrics = metrics_for(html)

    assert metrics.ctas_count == 3


def test_ctas_count_includes_role_button_links_without_a_cta_class():
    html = """
    <a href="/signup" class="bg-blue-600 text-white px-6 py-3 rounded-lg" role="button">Sign Up</a>
    <a href="/about">About</a>
    """
    metrics = metrics_for(html)

    assert metrics.ctas_count == 1


def test_links_split_internal_vs_external_and_normalize_www():
    html = """
    <a href="/relative-page">Relative</a>
    <a href="https://www.example.com/other">Same site, with www</a>
    <a href="https://external.com/page">External</a>
    """
    metrics = metrics_for(html, source_url="https://example.com/page")

    assert metrics.internal_links_count == 2
    assert metrics.external_links_count == 1


def test_links_exclude_non_navigational_schemes():
    html = """
    <a href="#section">Anchor</a>
    <a href="mailto:hello@example.com">Email</a>
    <a href="tel:+15551234567">Call</a>
    <a href="javascript:void(0)">JS</a>
    <a href="/real-page">Real link</a>
    """
    metrics = metrics_for(html)

    assert metrics.internal_links_count == 1
    assert metrics.external_links_count == 0


def test_image_missing_alt_counts_absent_and_empty_alt():
    html = """
    <img src="/a.png" alt="Descriptive text">
    <img src="/b.png">
    <img src="/c.png" alt="">
    """
    metrics = metrics_for(html)

    assert metrics.image_count == 3
    assert metrics.image_missing_alttext_percent == 67


def test_image_missing_alt_percent_is_zero_with_no_images():
    metrics = metrics_for("<p>No images on this page.</p>")

    assert metrics.image_count == 0
    assert metrics.image_missing_alttext_percent == 0


def test_meta_title_and_description_are_extracted_and_trimmed():
    html = """
    <head>
      <title>  Page Title  </title>
      <meta name="description" content="  Page summary.  ">
    </head>
    """
    metrics = metrics_for(html)

    assert metrics.meta_title == "Page Title"
    assert metrics.meta_description == "Page summary."


def test_meta_title_and_description_default_to_empty_string_when_missing():
    metrics = metrics_for("<p>No head metadata here.</p>")

    assert metrics.meta_title == ""
    assert metrics.meta_description == ""
