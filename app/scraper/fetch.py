import httpx

DEFAULT_TIMEOUT = 10.0
USER_AGENT = "Mozilla/5.0 (compatible; WebsiteAuditBot/1.0; +https://eight25media.com)"


class FetchError(Exception):
    """Raised when a URL cannot be fetched or does not return usable HTML."""


async def fetch_html(url: str, timeout: float = DEFAULT_TIMEOUT) -> str:
    """Fetch a URL and return its raw HTML body.

    Raises FetchError for network failures, non-2xx responses, or
    non-HTML content, so callers get one clear failure mode instead of
    a downstream parsing error.
    """
    headers = {"User-Agent": USER_AGENT}

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            response = await client.get(url, headers=headers)
    except httpx.RequestError as exc:
        raise FetchError(f"Failed to reach {url}: {exc}") from exc

    if response.status_code >= 400:
        raise FetchError(f"{url} returned status {response.status_code}")

    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type:
        raise FetchError(f"{url} did not return HTML content (got '{content_type}')")

    return response.text
