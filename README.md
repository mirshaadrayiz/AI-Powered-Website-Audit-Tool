# AI-Powered-Website-Audit-Tool
An automated website auditing tool that takes a URL as input, extracts factual, measurable metrics from the site, and uses AI to generate structured insights and prioritized recommendations.

## Architecture

The tool is split into two independent halves, wired together by a thin orchestrator. This separation is deliberate: factual metrics must never be conflated with AI-generated insights.

- **`app/scraper/`** — deterministic, no AI involved. Given a URL, produces factual metrics and cleaned page content.
  - `fetch.py` — fetches raw HTML over HTTP (`httpx`), raising a clear error on network failure, non-2xx status, or non-HTML content.
  - `parser.py` — parses HTML into a DOM (BeautifulSoup) and extracts human-readable page text, stripping non-content markup, sitewide chrome, and statically-detectable hidden elements.
  - `metrics.py` — computes every required factual metric (word count, heading counts + order, CTA count, internal/external links, image alt-text coverage, meta title/description) directly from the DOM.
  - `scrape.py` — the single public entry point, `scrape_page(url)`, gluing fetch → parse → metrics into one call.
- **`app/ai/`** — takes the scraper's output (metrics + content) and produces the AI-generated insights and recommendations. Never touches raw HTML directly — only the already-extracted facts and text.
  - `prompts.py` — the system prompt and `build_user_prompt(url, scraped_page)`, which packages the URL, factual metrics (as JSON), and page content into the model's input.
  - `client.py` — `generate_structured(system_prompt, user_prompt, schema)`, a thin Gemini wrapper that forces the model's output to match a given Pydantic schema and returns both the raw text and the parsed result.
- **`app/schemas.py`** — Pydantic models forming the contract boundary: `FactualMetricsSchema` (facts) is a distinct type from `InsightSchema`/`RecommendationSchema` (AI output), so the two are never conflated in the API response. `AIAnalysisSchema` (insights + recommendations only) is what gets forced as the model's structured output; `factual_metrics` is added afterward by the orchestrator, never by the model.
- **`app/web_audit_tool.py`** — `audit_website(url)`, the orchestrator: scrape → build prompt → call the model → assemble into `OutputSchema`. The one place the scraper and AI halves meet.
- **`app/main.py`** — the FastAPI app, one route (`POST /audit`). No `routes/`/`APIRouter` split — that pattern earns its keep with multiple resource groups to separate; this project has exactly one endpoint, so a single-file route is the right scope, not premature organization.

## Setup

```bash
uv sync
cp .env.example .env   # then add a Gemini API key — free, no card required: https://aistudio.google.com/apikey
uv run pytest        # run the test suite (27 tests)
```

## Running the API

```bash
uv run fastapi dev app/main.py
```

Then, in another terminal:
```bash
curl -X POST http://127.0.0.1:8000/audit \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

Interactive docs (Swagger UI) are auto-generated at `http://127.0.0.1:8000/docs`.

`POST /audit` takes `{"url": "..."}` (validated against `InputSchema`) and returns `OutputSchema` — `factual_metrics`, `insights`, and `recommendations`. A page that can't be fetched (network failure, non-2xx, non-HTML, bot-blocked) returns `422` with the underlying `FetchError` message; a Gemini API failure returns `502`.

## Prompt logs

Every call to the model is automatically logged to `logs/prompt_logs/`, one JSON file per call (`app/ai/prompt_logger.py`, wired into `generate_structured()` in `client.py`). Each file records:

- `system_prompt` — the exact system prompt text used
- `user_prompt` — the fully constructed user turn (URL, factual metrics as JSON, page content)
- `response_json_schema` — the JSON schema enforced on the model's output via Gemini's `response_json_schema`
- `raw_output` — the model's raw JSON text, before it's parsed or merged into the final response
- `parsed_output`, `model`, `timestamp`

This isn't a one-off manual step — logging happens automatically on every real call, so any run (including ones you make yourself) produces a fresh entry.

## AI provider

Uses **Google Gemini** (`gemini-3.6-flash` by default, pinned rather than a floating `-latest` alias — the system prompt is tuned against this specific model's behavior, so an alias that silently repoints to a newer model on Google's schedule could just as silently change the audit's output with no signal anything shifted; override with `GEMINI_MODEL` in `.env` if upgrading, and re-validate the prompt against the new model first), chosen specifically for its free tier: no credit card, roughly 1,500 requests/day and 10–15 requests/minute on Flash-tier models — comfortably enough for a single-page audit tool, with no billing setup required to run or review this project. Configured via `GEMINI_API_KEY` / `GEMINI_MODEL` in `.env` (see `app/config.py`), read through `pydantic-settings` so the app fails fast with a clear error if the key isn't set, rather than failing deep inside an API call.

## Design decisions & trade-offs

- **Metrics are computed in code, never by the LLM.** Word counts, heading counts, link counts, and alt-text coverage are exact, reproducible facts — an LLM asked to count these from raw HTML would approximate, and could give a different answer on every run of the same page. The AI layer only ever reasons over numbers `metrics.py` has already computed.
- **CTA detection is a heuristic, not a certainty.** A link is counted as a CTA if it's a `<button>`, a submit/button `<input>`, an `<a>` tag with `role="button"` (a real accessibility standard for "this link behaves like a button" — not a guess), or an `<a>` tag whose class name contains `btn`, `button`, or `cta` — conventions used by most site frameworks/themes. This still can't catch a link styled purely via Tailwind-style utility classes (e.g. `class="bg-blue-600 px-6 py-3 rounded-lg"`) with no `role` attribute and no semantic class name — full detection would require actually rendering the page's CSS.
- **Missing and decorative alt text are counted separately, not collapsed into one "missing" percentage.** `_image_stats()` distinguishes images with no `alt` attribute at all (`image_missing_alt_count` — a real accessibility gap) from images with `alt=""` present (`image_decorative_alt_count`) — the correct, WCAG-compliant way to mark a purely decorative image, not a defect. The system prompt explicitly tells the model never to treat `image_decorative_alt_count` as an accessibility problem or fold it into `image_missing_alt_count` when citing a number.
- **Every structural metric — word count, heading sequence, links, images, CTAs, meta title/description — is computed from the same cleaned copy of the DOM** (`strip_chrome()` in `parser.py`), which removes both sitewide chrome (`<nav>`/`<header>`/`<footer>`) and conditionally-rendered fallback content (`<noscript>`, `<video>`/`<audio>`/`<canvas>`/`<object>` fallbacks) before any metric is counted — `<head>`/`<script>`/`<style>` stay a text-extraction-only concern, since they hold non-body or non-markup content that can't produce a stray heading/link/image. This consistency matters because the system prompt tells the model to read `heading_counts.sequence` directly to detect hierarchy problems (a missing H1, an H1→H3 jump) and to compare link count against word count as a directory-vs-landing-page signal — both only hold up if every metric shares the same scope, so a nav `<h2>` or a link buried in `<video>` fallback text can't manufacture a false hierarchy finding or inflate the link ratio. Relies on semantic HTML5 tags for the chrome case; a site that wraps its nav/footer in plain `<div>`s instead won't be caught.
- **Hidden-element detection only catches what's visible in static HTML.** Elements with the `hidden` attribute or an inline `display:none`/`visibility:hidden` style are excluded from word count, since no visitor — sighted or not — sees that text. Deliberately excludes `aria-hidden="true"`: that attribute only hides content from screen readers, not from visual rendering, so a sighted visitor still sees it. There's also an inherent, unresolvable ambiguity here: `display:none` at parse time looks identical whether it's a legitimate accordion/tab panel (revealed on click, real users do read it) or actual keyword-stuffing cloaking (a black-hat SEO technique) — static HTML parsing with no JS execution can't tell these apart.
- **Internal vs. external links are classified by normalized domain** (`www.` stripped), after resolving relative URLs against the page's own URL. `#anchor`, `mailto:`, `tel:`, and `javascript:` links are excluded since they aren't page-to-page navigation. `internal_links_count`/`external_links_count` count every `<a>` instance, so the same destination linked from a title, a thumbnail, and a duplicated mobile/desktop nav block all count separately; `unique_internal_links_count`/`unique_external_links_count` deduplicate by resolved destination (fragment ignored) instead, and are what the system prompt is told to use for the directory-vs-content-page signal.
- **No headless browser / JS execution.** The scraper is a plain HTTP client (`httpx`), so any site that requires JavaScript to render content, or gates access behind a bot-detection challenge (e.g. Cloudflare's "Just a moment..." interstitial), can't be scraped. Confirmed against a real Cloudflare-protected site, where the tool correctly raised a clear `FetchError: ... returned status 403` rather than silently treating the challenge page as real content.
- **`generate_structured()` pins `temperature=0`, a capped `max_output_tokens`, and `thinking_level=MINIMAL`.** An audit is meant to be reproducible — a human re-running the same URL should get the same findings, not a different set of insights each time from sampling variance. Thinking is set to the model's lowest level rather than left unset: this is bounded structured extraction over metrics already computed in code, not open-ended reasoning, so a Flash-tier model's default (dynamic, variable-latency) thinking buys nothing here while adding unpredictable latency. (`thinking_budget=0`, the numeric equivalent on older Gemini models, isn't accepted by this model — confirmed by a live 400 against the real API — hence the level-based field instead.)
- **Each recommendation cites the exact metric(s) it's grounded in, and the citations are verified against the real computed metrics, not just requested in the prompt.** `RecommendationReasoningSchema.metrics_cited` holds `"field_name: value"` strings (e.g. `"total_word_count: 263"`); `app/ai/grounding.py`'s `find_ungrounded_citations()` checks each one against the actual `FactualMetricsSchema` for that page and logs a warning for any that don't match — a hallucinated or misremembered number is now something the code can actually catch, not just something the prompt asks the model not to do. Deliberately a one-shot check, not a verify-and-retry loop: matching is exact-value, not fuzzy, so it can't validate a paraphrased or rounded citation ("roughly 260 words"), and this project's free-tier Gemini quota (20 requests/day) is too thin to spend on an additional retry pass per audit.
- **Structured output is enforced by the API, not by prompt text.** `client.py` passes the Pydantic schema to Gemini via a dedicated `response_json_schema` parameter — the model's output is constrained at the decoding level to match it, which is why the schema itself never appears as text inside `SYSTEM_PROMPT`. The prompt's job is entirely different: guiding what *content* belongs in each field (grounding rules, how to read `heading_counts.sequence`, the CTA-count caveat), not describing the JSON shape.
- **Structural-signal guidance had to be broadened after real-world testing.** The first version of `SYSTEM_PROMPT` gave `structural_concerns` only one example (heading hierarchy), and the model anchored on it almost exclusively, ignoring link-density and CTA-distribution signals that were already present in the same data. Broadening the prompt to name all three signals — without a schema or code change — fixed it; confirmed by re-running the same URL before and after and diffing the output.
- **API errors are mapped to specific status codes, not a blanket 500.** `FetchError` (scrape failed) → `422`; `AIError` (Gemini failed after retries) → `502`. `generate_structured()` retries timeouts, connection errors, 408/5xx responses, and schema-violating output up to `MAX_ATTEMPTS` with exponential backoff, and sets a hard per-request timeout so a hung upstream can't block the request forever. `429` is deliberately excluded from the retry set: on this project's 20-request/day free-tier quota, a `429` almost always means the quota is exhausted rather than a transient throttle, and no amount of exponential backoff (seconds) closes the gap to a daily reset — retrying would just burn up to `MAX_ATTEMPTS` more requests for no chance of success — the SDK's own client otherwise defaults to no timeout at all. Every attempt, successful or not, is logged to `logs/prompt_logs/`. Once retries are exhausted, the underlying `google.genai.errors.APIError` (or timeout/validation error) is wrapped in `AIError` and raised; `main.py` catches that wrapper rather than the raw SDK exception, so a genuine bug in our own code still surfaces as an unhandled 500 instead of being silently mislabeled as an upstream AI failure.

### Validation

Every metric was cross-checked against a real, large page (565KB HTML, 1200+ links) by independently fetching it (`curl`, separate from the app's `httpx` client) and independently re-implementing the metric definitions in a standalone script — every field matched exactly.

## What I'd improve with more time

- Headless-browser fallback (Playwright) for JS-rendered or bot-protected pages.
- Detect boilerplate wrapped in `<div>`s instead of semantic `<nav>`/`<header>`/`<footer>` tags (e.g. via common class/id naming conventions).
- Surface "% of page text hidden by default" as its own factual metric, so the AI layer can explicitly flag potential keyword-stuffing risk instead of the fact being silently absorbed into word count.
- SSRF hardening and a response size cap in `fetch.py` — it currently fetches any user-supplied URL with no IP/scheme allowlist and no body size limit, so an internal address (e.g. a cloud metadata endpoint) or an oversized response goes straight through. Fine for local/personal use; needed before this is deployed as a service anyone can point at arbitrary URLs.
- Turn metric-citation grounding from a logged warning into a real verify-and-retry loop: on an ungrounded citation, re-call the model once with the specific mismatch as feedback instead of just logging it, and extend the same `metrics_cited` grounding to insights, not just recommendations. Held back for now since it doubles API calls on failure against a 20-request/day free-tier quota, and insight fields are currently plain strings, not objects — grounding those means restructuring `InsightSchema` first.
- Smarter 429 handling: right now any `429` just fails fast (see above). Gemini's error details distinguish per-minute throttling from daily-quota exhaustion and can include a `Retry-After`-style hint — reading that would let a short-lived throttle still retry (with a wait long enough to matter) while a daily-quota 429 keeps failing fast, instead of treating every `429` the same way.
