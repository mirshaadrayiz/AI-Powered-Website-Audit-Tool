from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.schemas import FactualMetricsSchema, HeadingCountsSchema
from app.scraper.parser import text_from_scope

# Class-name conventions used across most site frameworks/themes (Bootstrap,
# Tailwind, WordPress) to mark an anchor as a styled action button rather
# than an inline text link. A heuristic, not a guarantee — documented as a
# trade-off since CTA styling can't be reliably detected from markup alone.
CTA_CLASS_HINTS = ("btn", "button", "cta")

# Links that don't represent navigation to another page and shouldn't be
# counted as internal/external.
NON_NAVIGATIONAL_SCHEMES = ("#", "mailto:", "tel:", "javascript:")


def _word_count(soup: BeautifulSoup) -> int:
    return len(text_from_scope(soup).split())


def _heading_counts(soup: BeautifulSoup) -> HeadingCountsSchema:
    sequence = [tag.name for tag in soup.find_all(["h1", "h2", "h3"])]
    return HeadingCountsSchema(
        h1_count=sequence.count("h1"),
        h2_count=sequence.count("h2"),
        h3_count=sequence.count("h3"),
        sequence=sequence,
    )


def _looks_like_cta_link(tag) -> bool:
    if tag.get("role", "").strip().lower() == "button":
        return True

    classes = " ".join(tag.get("class", [])).lower()
    return any(hint in classes for hint in CTA_CLASS_HINTS)


def _count_ctas(soup: BeautifulSoup) -> int:
    buttons = soup.find_all("button")
    submit_inputs = soup.find_all("input", attrs={"type": ["button", "submit"]})
    cta_links = [a for a in soup.find_all("a", href=True) if _looks_like_cta_link(a)]
    return len(buttons) + len(submit_inputs) + len(cta_links)


def _normalize_netloc(netloc: str) -> str:
    return netloc.lower().removeprefix("www.")


def _count_links(soup: BeautifulSoup, source_url: str) -> tuple[int, int, int, int]:
    """Return (internal, external, unique internal, unique external).

    internal/external count every navigational <a> tag instance; unique_*
    dedupes by resolved destination (fragment ignored), so the same link
    repeated in multiple places on the page only counts once.
    """
    source_netloc = _normalize_netloc(urlparse(source_url).netloc)
    internal = 0
    external = 0
    unique_internal = set()
    unique_external = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.lower().startswith(NON_NAVIGATIONAL_SCHEMES):
            continue

        resolved = urlparse(urljoin(source_url, href))
        destination = resolved._replace(fragment="").geturl()

        if _normalize_netloc(resolved.netloc) == source_netloc:
            internal += 1
            unique_internal.add(destination)
        else:
            external += 1
            unique_external.add(destination)

    return internal, external, len(unique_internal), len(unique_external)


def _image_stats(soup: BeautifulSoup) -> tuple[int, int, int]:
    """Return (total images, missing alt, decorative alt).

    "Missing" (no alt attribute at all) and "decorative" (alt="" present but
    empty) are counted separately — the latter is correct, WCAG-compliant
    markup for a purely decorative image, not an accessibility defect.
    """
    images = soup.find_all("img")
    missing_alt = sum(1 for img in images if not img.has_attr("alt"))
    decorative_alt = sum(1 for img in images if img.has_attr("alt") and not img["alt"].strip())
    return len(images), missing_alt, decorative_alt


def _meta_title(soup: BeautifulSoup) -> str:
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    return ""


def _meta_description(soup: BeautifulSoup) -> str:
    tag = soup.find("meta", attrs={"name": "description"})
    if tag and tag.get("content"):
        return tag["content"].strip()
    return ""


def extract_metrics(content_soup: BeautifulSoup, source_url: str) -> FactualMetricsSchema:
    """Compute deterministic, reproducible page metrics from an already-scoped DOM."""
    internal_links, external_links, unique_internal_links, unique_external_links = _count_links(
        content_soup, source_url
    )
    image_count, missing_alt_count, decorative_alt_count = _image_stats(content_soup)
    meta_title = _meta_title(content_soup)
    meta_description = _meta_description(content_soup)

    return FactualMetricsSchema(
        total_word_count=_word_count(content_soup),
        heading_counts=_heading_counts(content_soup),
        ctas_count=_count_ctas(content_soup),
        internal_links_count=internal_links,
        external_links_count=external_links,
        unique_internal_links_count=unique_internal_links,
        unique_external_links_count=unique_external_links,
        image_count=image_count,
        image_missing_alt_count=missing_alt_count,
        image_decorative_alt_count=decorative_alt_count,
        meta_title=meta_title,
        meta_title_length=len(meta_title),
        meta_description=meta_description,
        meta_description_length=len(meta_description),
    )
