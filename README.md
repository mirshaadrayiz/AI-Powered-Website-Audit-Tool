# AI-Powered-Website-Audit-Tool
An automated website auditing tool that takes a URL as input, extracts factual, measurable metrics from the site, and uses AI to generate structured insights and prioritized recommendations.

## Architecture

The tool is split into two independent halves, wired together by a thin orchestrator. This separation is deliberate: factual metrics must never be conflated with AI-generated insights.

- **`app/scraper/`** — deterministic, no AI involved. Given a URL, produces factual metrics and cleaned page content.
  - `fetch.py` — fetches raw HTML over HTTP (`httpx`), raising a clear error on network failure, non-2xx status, or non-HTML content.
  - `parser.py` — parses HTML into a DOM (BeautifulSoup) and extracts human-readable page text, stripping non-content markup, sitewide chrome, and statically-detectable hidden elements.
  - `metrics.py` — computes every required factual metric (word count, heading counts + order, CTA count, internal/external links, image alt-text coverage, meta title/description) directly from the DOM.
  - `scrape.py` — the single public entry point, `scrape_page(url)`, gluing fetch → parse → metrics into one call.
- **`app/ai/`** *(in progress)* — takes the scraper's output (metrics + content) and produces the AI-generated insights and recommendations. Never touches raw HTML directly — only the already-extracted facts and text.
- **`app/schemas.py`** — Pydantic models forming the contract boundary: `FactualMetricsSchema` (facts) is a distinct type from `InsightSchema`/`RecommendationSchema` (AI output), so the two are never conflated in the API response.

## Setup

```bash
uv sync
cp .env.example .env   # then add a Gemini API key — free, no card required: https://aistudio.google.com/apikey
uv run pytest        # run the test suite (app/scraper, 20 tests)
```

Manual smoke test against a real URL:
```bash
uv run -m app.scraper.scrape
```
(edit the hardcoded `url` at the bottom of `scrape.py` to point at a different page)

Manual smoke test of the AI client:
```bash
uv run -m app.ai.client
```

## AI provider

Uses **Google Gemini** (`gemini-2.5-flash` by default), chosen specifically for its free tier: no credit card, roughly 1,500 requests/day and 10–15 requests/minute on Flash-tier models — comfortably enough for a single-page audit tool, with no billing setup required to run or review this project. Configured via `GEMINI_API_KEY` / `GEMINI_MODEL` in `.env` (see `app/config.py`), read through `pydantic-settings` so the app fails fast with a clear error if the key isn't set, rather than failing deep inside an API call.

## Design decisions & trade-offs

- **Metrics are computed in code, never by the LLM.** Word counts, heading counts, link counts, and alt-text coverage are exact, reproducible facts — an LLM asked to count these from raw HTML would approximate, and could give a different answer on every run of the same page. The AI layer only ever reasons over numbers `metrics.py` has already computed.
- **CTA detection is a heuristic, not a certainty.** A link is counted as a CTA if it's a `<button>`, a submit/button `<input>`, an `<a>` tag with `role="button"` (a real accessibility standard for "this link behaves like a button" — not a guess), or an `<a>` tag whose class name contains `btn`, `button`, or `cta` — conventions used by most site frameworks/themes. This still can't catch a link styled purely via Tailwind-style utility classes (e.g. `class="bg-blue-600 px-6 py-3 rounded-lg"`) with no `role` attribute and no semantic class name — full detection would require actually rendering the page's CSS.
- **Word count and the text handed to the AI layer exclude `<head>`, `<script>`, `<style>`, `<noscript>`, and `<nav>`/`<header>`/`<footer>`.** The first group is never rendered as body content at all (e.g. `<title>` shows in a browser tab, not on the page). The landmark tags are excluded so sitewide chrome — identical across every page of a site — doesn't inflate word count or dilute the "content depth" signal fed to the AI. This relies on semantic HTML5 tags; a site that wraps its nav/footer in plain `<div>`s instead won't be caught.
- **Hidden-element detection only catches what's visible in static HTML.** Elements with the `hidden` attribute or an inline `display:none`/`visibility:hidden` style are excluded from word count, since no visitor — sighted or not — sees that text. Deliberately excludes `aria-hidden="true"`: that attribute only hides content from screen readers, not from visual rendering, so a sighted visitor still sees it. There's also an inherent, unresolvable ambiguity here: `display:none` at parse time looks identical whether it's a legitimate accordion/tab panel (revealed on click, real users do read it) or actual keyword-stuffing cloaking (a black-hat SEO technique) — static HTML parsing with no JS execution can't tell these apart.
- **Internal vs. external links are classified by normalized domain** (`www.` stripped), after resolving relative URLs against the page's own URL. `#anchor`, `mailto:`, `tel:`, and `javascript:` links are excluded since they aren't page-to-page navigation.
- **No headless browser / JS execution.** The scraper is a plain HTTP client (`httpx`), so any site that requires JavaScript to render content, or gates access behind a bot-detection challenge (e.g. Cloudflare's "Just a moment..." interstitial), can't be scraped. Confirmed against a real Cloudflare-protected site, where the tool correctly raised a clear `FetchError: ... returned status 403` rather than silently treating the challenge page as real content.

### Validation

Every metric was cross-checked against a real, large page (565KB HTML, 1200+ links) by independently fetching it (`curl`, separate from the app's `httpx` client) and independently re-implementing the metric definitions in a standalone script — every field matched exactly.

## What I'd improve with more time

- Headless-browser fallback (Playwright) for JS-rendered or bot-protected pages.
- Detect boilerplate wrapped in `<div>`s instead of semantic `<nav>`/`<header>`/`<footer>` tags (e.g. via common class/id naming conventions).
- Surface "% of page text hidden by default" as its own factual metric, so the AI layer can explicitly flag potential keyword-stuffing risk instead of the fact being silently absorbed into word count.
