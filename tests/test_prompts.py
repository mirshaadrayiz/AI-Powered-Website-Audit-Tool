from app.llm.prompts import MAX_CONTENT_CHARS, build_user_prompt
from app.scraper.scrape import ScrapedPage


def test_build_user_prompt_includes_url_metrics_and_untruncated_content(make_metrics):
    page = ScrapedPage(metrics=make_metrics(total_word_count=263), content="Hello world")

    prompt = build_user_prompt("https://example.com", page)

    assert "Audit this page: https://example.com" in prompt
    assert '"total_word_count": 263' in prompt
    assert "PAGE TEXT CONTENT:" in prompt
    assert "showing the first" not in prompt
    assert "<untrusted_page_content>\nHello world\n</untrusted_page_content>" in prompt


def test_build_user_prompt_truncates_long_content_and_labels_it(make_metrics):
    words = [f"word{i}" for i in range(3000)]
    long_content = " ".join(words)
    total_chars = len(long_content)
    assert total_chars > MAX_CONTENT_CHARS

    page = ScrapedPage(metrics=make_metrics(), content=long_content)

    prompt = build_user_prompt("https://example.com", page)

    assert f"showing the first {MAX_CONTENT_CHARS:,} of {total_chars:,} characters" in prompt
    assert "word0" in prompt
    assert "word2999" not in prompt
