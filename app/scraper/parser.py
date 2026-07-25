import copy
import re

from bs4 import BeautifulSoup

# Markup that isn't rendered in the page body at all. <head> is included
# because none of its children (title, meta, link) render as body content —
# title text shows in a browser tab, not on the page.
MARKUP_NOISE_TAGS = ["head", "script", "style", "noscript"]

# Structural chrome repeated on every page of a site (nav, header, footer).
# Stripped so word count and the text handed to the AI layer reflect this
# page's actual content, not sitewide boilerplate. Relies on semantic HTML5
# tags — a site that wraps nav/footer in plain <div>s instead won't be caught.
BOILERPLATE_LANDMARK_TAGS = ["nav", "header", "footer"]

_HIDDEN_STYLE_PATTERN = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden", re.IGNORECASE)


def parse_html(html: str) -> BeautifulSoup:
    """Parse raw HTML into a queryable DOM tree.

    lxml is used for its speed and tolerance of malformed real-world HTML.
    """
    return BeautifulSoup(html, "lxml")


def _is_hidden(tag) -> bool:
    """Detect elements that are visually hidden from every viewer.

    Deliberately does NOT check aria-hidden: that attribute hides an
    element from the accessibility tree (screen readers), not from visual
    rendering — a sighted visitor still sees it, so treating it as "not
    visible text" would wrongly strip real page content.

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


def extract_visible_text(soup: BeautifulSoup) -> str:
    """Return the page's human-readable content text.

    Excludes non-content markup (script/style/noscript), sitewide chrome
    (nav/header/footer), and statically-detectable hidden elements.
    Operates on a copy so callers can keep using the original `soup` for
    tag-based metrics (headings, links, images, CTAs) afterwards — those
    should still see nav/footer links and CTAs, only the text extraction
    scopes down to page content.
    """
    working_copy = copy.copy(soup)

    for tag in working_copy(MARKUP_NOISE_TAGS + BOILERPLATE_LANDMARK_TAGS):
        tag.decompose()

    for tag in working_copy.find_all(True):
        if tag.parent is not None and _is_hidden(tag):
            tag.decompose()

    return " ".join(working_copy.get_text(separator=" ").split())
