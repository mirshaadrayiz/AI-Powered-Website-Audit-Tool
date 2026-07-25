import asyncio

from app.scraper.scrape import scrape_page

SAMPLE_HTML = """
<html>
<head>
  <title>Sample Page</title>
  <meta name="description" content="A sample page for testing.">
</head>
<body>
  <header><nav><a href="/">Home</a></nav></header>
  <main>
    <h1>Welcome</h1>
    <p>Some real content goes here.</p>
    <a href="/signup" class="btn">Sign Up</a>
  </main>
  <footer><p>Copyright</p></footer>
</body>
</html>
"""


def test_scrape_page_combines_metrics_and_content(monkeypatch):
    async def fake_fetch_html(url: str, timeout: float = 10.0) -> str:
        assert url == "https://example.com/page"
        return SAMPLE_HTML

    monkeypatch.setattr("app.scraper.scrape.fetch_html", fake_fetch_html)

    page = asyncio.run(scrape_page("https://example.com/page"))

    assert page.metrics.meta_title == "Sample Page"
    assert page.metrics.meta_description == "A sample page for testing."
    assert page.metrics.heading_counts.h1_count == 1
    assert page.metrics.ctas_count == 1
    assert page.content == "Welcome Some real content goes here. Sign Up"
