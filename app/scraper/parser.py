import copy
import re

from bs4 import BeautifulSoup

# Markup that isn't rendered in the page body at all. 
MARKUP_NOISE_TAGS = ["head", "script", "style"]

# Structural chrome repeated on every page of a site (nav, header, footer).
BOILERPLATE_LANDMARK_TAGS = ["nav", "header", "footer"]

# Content only rendered conditionally — <noscript> when JS is disabled;
# <video>/<audio>/<canvas>/<object> fallback content when the browser can't
# render the element at all. A real visitor essentially never sees any of this
FALLBACK_CONTENT_TAGS = ["noscript", "video", "audio", "canvas", "object"]

_HIDDEN_STYLE_PATTERN = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden", re.IGNORECASE)


def parse_html(html: str) -> BeautifulSoup:
    """Parse raw HTML into a queryable DOM tree."""
    return BeautifulSoup(html, "lxml")


def _is_hidden(tag) -> bool:
    """Detect elements that are visually hidden from every viewer."""
    if tag.has_attr("hidden"):
        return True
    style = tag.get("style", "")
    return bool(style and _HIDDEN_STYLE_PATTERN.search(style))


def strip_chrome(soup: BeautifulSoup) -> BeautifulSoup:
    """Return a copy of the DOM scoped to this page's real, always-visible content."""
    working_copy = copy.copy(soup)
    for tag in working_copy.find_all(BOILERPLATE_LANDMARK_TAGS + FALLBACK_CONTENT_TAGS):
        tag.decompose()
    for tag in working_copy.find_all(True):
        if tag.parent is not None and _is_hidden(tag):
            tag.decompose()
    return working_copy


def text_from_scope(soup: BeautifulSoup) -> str:
    """Return the human-readable text of a soup already scoped by strip_chrome."""
    working_copy = copy.copy(soup)
    for tag in working_copy.find_all(MARKUP_NOISE_TAGS):
        tag.decompose()
    return " ".join(working_copy.get_text(separator=" ").split())


def extract_visible_text(soup: BeautifulSoup) -> str:
    """Return the page's human-readable content text."""
    return text_from_scope(strip_chrome(soup))
