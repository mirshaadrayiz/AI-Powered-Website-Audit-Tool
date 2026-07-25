from app.scraper.parser import extract_visible_text, parse_html


def test_excludes_script_style_and_noscript():
    html = """
    <script>var hidden = "script text";</script>
    <style>.a { color: red; }</style>
    <noscript>Enable JavaScript text</noscript>
    <p>Real content here.</p>
    """
    text = extract_visible_text(parse_html(html))

    assert text == "Real content here."


def test_excludes_head_contents_like_title():
    html = """
    <head><title>Page Title</title><meta name="description" content="desc"></head>
    <body><p>Real content.</p></body>
    """
    text = extract_visible_text(parse_html(html))

    assert text == "Real content."


def test_excludes_nav_header_and_footer_boilerplate():
    html = """
    <header><nav><a href="/">Home</a><a href="/about">About</a></nav></header>
    <main><p>The actual page content.</p></main>
    <footer><p>Copyright 2026 Example Co.</p></footer>
    """
    text = extract_visible_text(parse_html(html))

    assert text == "The actual page content."


def test_excludes_elements_hidden_via_hidden_attribute():
    html = '<p>Visible.</p><p hidden>Not visible.</p>'
    text = extract_visible_text(parse_html(html))

    assert text == "Visible."


def test_does_not_exclude_aria_hidden_text_since_it_is_still_visually_shown():
    html = '<p>Visible.</p><p aria-hidden="true">Also visually visible.</p>'
    text = extract_visible_text(parse_html(html))

    assert text == "Visible. Also visually visible."


def test_excludes_elements_hidden_via_inline_style():
    html = """
    <p>Visible.</p>
    <p style="display: none;">Not visible display.</p>
    <p style="visibility:hidden">Not visible visibility.</p>
    """
    text = extract_visible_text(parse_html(html))

    assert text == "Visible."


def test_excludes_nested_hidden_element_without_error():
    html = '<div hidden><p>Not visible.</p><span>Also not visible.</span></div><p>Visible.</p>'
    text = extract_visible_text(parse_html(html))

    assert text == "Visible."


def test_does_not_mutate_the_original_soup():
    soup = parse_html('<header><nav>Nav</nav></header><script>x</script><p hidden>H</p><p>Visible</p>')
    extract_visible_text(soup)

    assert soup.find("header") is not None
    assert soup.find("script") is not None
    assert soup.find("p", attrs={"hidden": True}) is not None
