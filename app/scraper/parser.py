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
    """Parse raw HTML into a queryable DOM tree.

    lxml is used for its speed and tolerance of malformed real-world HTML.
    """
    return BeautifulSoup(html, "lxml")


def _is_hidden(tag) -> bool:
    """Detect elements that are visually hidden from every viewer.

    Also a static-HTML tool with no CSS/JS execution, so this only catches
    hiding done inline or via HTML attributes — not visibility controlled
    by an external stylesheet or a class toggled at runtime (e.g. an
    accordion/tab panel revealed on click looks identical, in raw HTML, to
    text hidden for keyword-stuffing purposes). Documented as a known
    limitation rather than something this tool can resolve.
    """
    if tag.has_attr("hidden"):
        return True
    style = tag.get("style", "")
    return bool(style and _HIDDEN_STYLE_PATTERN.search(style))


def strip_chrome(soup: BeautifulSoup) -> BeautifulSoup:
    """Return a copy of the DOM scoped to this page's real, always-visible content.

    Removes sitewide chrome (nav/header/footer), conditionally-rendered
    fallback content (noscript/video/audio/canvas/object), and
    statically-detectable hidden elements — see BOILERPLATE_LANDMARK_TAGS,
    FALLBACK_CONTENT_TAGS, and _is_hidden. This is the single scope every
    metric — heading sequence, links, images, CTAs, word count — is computed
    from, so they all describe content a real visitor sees, not boilerplate,
    fallback markup, or hidden elements. Operates on a copy; the original
    `soup` is never mutated.
    """
    working_copy = copy.copy(soup)
    for tag in working_copy.find_all(BOILERPLATE_LANDMARK_TAGS + FALLBACK_CONTENT_TAGS):
        tag.decompose()
    for tag in working_copy.find_all(True):
        if tag.parent is not None and _is_hidden(tag):
            tag.decompose()
    return working_copy


def text_from_scope(soup: BeautifulSoup) -> str:
    """Return the human-readable text of a soup already scoped by strip_chrome.

    Only removes non-content markup (head/script/style) — everything else is
    assumed already handled by the caller's strip_chrome pass, so this never
    re-runs it. Operates on a copy; the original `soup` is never mutated.
    """
    working_copy = copy.copy(soup)
    for tag in working_copy.find_all(MARKUP_NOISE_TAGS):
        tag.decompose()
    return " ".join(working_copy.get_text(separator=" ").split())


def extract_visible_text(soup: BeautifulSoup) -> str:
    """Return the page's human-readable content text.

    Excludes non-content markup (head/script/style), everything strip_chrome
    already removes (sitewide chrome, fallback content, hidden elements).
    Operates on a copy; the original `soup` is never mutated.
    """
    return text_from_scope(strip_chrome(soup))
