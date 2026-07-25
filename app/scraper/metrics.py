from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.schemas import FactualMetricsSchema, HeadingCountsSchema
from app.scraper.parser import extract_visible_text

# Class-name conventions used across most site frameworks/themes (Bootstrap,
# Tailwind, WordPress) to mark an anchor as a styled action button rather
# than an inline text link. A heuristic, not a guarantee — documented as a
# trade-off since CTA styling can't be reliably detected from markup alone.
CTA_CLASS_HINTS = ("btn", "button", "cta")

# Links that don't represent navigation to another page and shouldn't be
# counted as internal/external.
NON_NAVIGATIONAL_SCHEMES = ("#", "mailto:", "tel:", "javascript:")


def _word_count(soup: BeautifulSoup) -> int:
    return len(extract_visible_text(soup).split())


def _heading_counts(soup: BeautifulSoup) -> HeadingCountsSchema:
    sequence = [tag.name for tag in soup.find_all(["h1", "h2", "h3"])]
    return HeadingCountsSchema(
        h1_count=sequence.count("h1"),
        h2_count=sequence.count("h2"),
        h3_count=sequence.count("h3"),
        sequence=sequence,
    )


def _looks_like_cta_link(tag) -> bool:
    # role="button" is an explicit, standard accessibility signal — not a
    # guess — for "this link behaves like a button." Catches CTAs styled
    # with utility classes (e.g. Tailwind) that CTA_CLASS_HINTS can't see,
    # since those don't use a semantic "btn"/"cta" class name at all.
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


def _count_links(soup: BeautifulSoup, source_url: str) -> tuple[int, int]:
    source_netloc = _normalize_netloc(urlparse(source_url).netloc)
    internal = 0
    external = 0

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(NON_NAVIGATIONAL_SCHEMES):
            continue

        resolved_netloc = _normalize_netloc(urlparse(urljoin(source_url, href)).netloc)
        if resolved_netloc == source_netloc:
            internal += 1
        else:
            external += 1

    return internal, external


def _image_stats(soup: BeautifulSoup) -> tuple[int, int]:
    images = soup.find_all("img")
    missing_alt = sum(1 for img in images if not img.get("alt", "").strip())
    return len(images), missing_alt


def _meta_title(soup: BeautifulSoup) -> str:
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    return ""


def _meta_description(soup: BeautifulSoup) -> str:
    tag = soup.find("meta", attrs={"name": "description"})
    if tag and tag.get("content"):
        return tag["content"].strip()
    return ""


def extract_metrics(soup: BeautifulSoup, source_url: str) -> FactualMetricsSchema:
    """Compute deterministic, reproducible page metrics from a parsed DOM.

    No model calls here — every field is a plain count or string pulled
    straight from the markup, so the same page always yields the same
    numbers.
    """
    internal_links, external_links = _count_links(soup, source_url)
    image_count, missing_alt = _image_stats(soup)
    missing_alt_percent = round((missing_alt / image_count) * 100) if image_count else 0

    return FactualMetricsSchema(
        total_word_count=_word_count(soup),
        heading_counts=_heading_counts(soup),
        ctas_count=_count_ctas(soup),
        internal_links_count=internal_links,
        external_links_count=external_links,
        image_count=image_count,
        image_missing_alttext_percent=missing_alt_percent,
        meta_title=_meta_title(soup),
        meta_description=_meta_description(soup),
    )
