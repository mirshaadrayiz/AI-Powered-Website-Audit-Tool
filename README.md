# AI-Powered Website Audit Tool

## Overview

Takes a URL, extracts factual, measurable metrics from the page, and uses an LLM to turn those
metrics into structured insights and prioritized recommendations. Available as a JSON API, a
single-page web UI, and a CLI.

The core idea: keep facts and AI opinions separate. Metrics are computed by deterministic code; the
AI layer only interprets what the code already measured, and never invents or overwrites a number.

## Architecture

```mermaid
flowchart TD
    URL(["URL"])
    SCRAPER["<b>Scraper</b><br/><i>deterministic, no AI</i><br/>fetch.py → parser.py → metrics.py"]
    AI["<b>AI layer</b><br/><i>Gemini Flash</i><br/>prompts.py → client.py"]
    OUT(["<b>Audit response</b><br/>metrics + insights + recommendations"])

    URL --> SCRAPER --> AI --> OUT
    SCRAPER -.->|"metrics, unchanged"| OUT

    classDef fact fill:#e7f0fb,stroke:#3f72ab,color:#12233b
    classDef ai fill:#f2e8fb,stroke:#7d4faf,color:#26123a
    classDef io fill:#eceef1,stroke:#5b6472,color:#1f2937
    class SCRAPER fact
    class AI ai
    class URL,OUT io
```

- **The scraper is deterministic.** Every metric is computed in code from the cleaned page. No AI
  involved, so the same page always produces the same numbers.

- **The AI layer never sees raw HTML.** It only receives the computed metrics and the page's visible
  text, and only reasons about what they mean.

- **Facts and AI output never mix.** The model's output schema holds insights and recommendations
  only. The metrics block is attached afterward, copied straight from the scraper (the dashed line in
  the diagram). The model can't change a single number it was given.

## Project structure

```
app/
├── llm/                   # AI layer: prompt construction + Gemini client
│   ├── client.py
│   ├── prompt_logger.py
│   └── prompts.py
├── scraper/               # Deterministic metric extraction
│   ├── fetch.py
│   ├── metrics.py
│   ├── parser.py
│   └── scrape.py
├── static/
│   └── index.html         # Web UI
├── config.py              # Settings, loaded from .env
├── main.py                # FastAPI app and the /audit route
├── schemas.py             # Pydantic models, the API contract
└── web_audit_tool.py      # Orchestrator: scrape -> AI -> response

tests/
├── conftest.py
├── test_client.py
├── test_fetch.py
├── test_main.py
├── test_metrics.py
├── test_parser.py
├── test_prompts.py
├── test_scrape.py
└── test_web_audit_tool.py

pyproject.toml
.env.example
```

Each package also has an `__init__.py`, omitted above for brevity.

## Setup

```bash
uv sync
cp .env.example .env   # add your Gemini API key
uv run pytest          # optional, 45 tests
```

Uses **Google Gemini `gemini-3.6-flash`**. Get a free key at
<https://aistudio.google.com/apikey>, no credit card required, and set it as `GEMINI_API_KEY`.

## Running

```bash
uv run fastapi dev app/main.py
```

- **Web UI:** <http://127.0.0.1:8000>

- **Swagger UI:** <http://127.0.0.1:8000/docs>

- **API:** `POST /audit` with `{"url": "..."}`:

  ```bash
  curl -X POST http://127.0.0.1:8000/audit \
    -H "Content-Type: application/json" \
    -d '{"url": "https://example.com"}'
  ```

- **CLI:** no server needed, prints the same JSON:

  ```bash
  uv run -m app.web_audit_tool https://example.com
  ```

Errors use distinct codes rather than a blanket 500: `422` means the page couldn't be fetched
(network failure, non-2xx, non-HTML, bot-blocked); `502` means the AI provider failed. A caller can
tell "this page is unauditable" apart from "the model is unavailable".

## Prompt logs

Every successful model call writes a plain-text file to `logs/`: the exact system prompt, the user
prompt, the schema name, the model's raw output, and the parsed result. Sections are labeled plain
text, not an escaped JSON blob, so they're easy to read. This happens automatically on every real
call, so there's nothing to enable.

## Design decisions & trade-offs

- **A free model was a deliberate constraint.** Gemini Flash requires no billing setup, which makes the project easy to run and review. The trade-off is a limited daily quota, so the audit uses a single model call instead of multi-step AI pipelines.

- **Metrics are computed deterministically, not by the model.** Counts such as words, headings, links, and CTAs come directly from the scraper. The AI layer only interprets these facts, preventing the model from inventing or changing measurements.

- **Insights are grounded in metrics.** Every insight and recommendation includes the exact metric fields it is based on. This keeps the reasoning traceable, although validation is currently enforced at the prompt level rather than checked in code.

- **The model is tuned for consistent output.** Temperature 0 and structured output keep audits reproducible. The model is used for interpretation and recommendations, not open-ended generation.

- **The prompt teaches the model how to interpret metrics.** Some metrics need context: heading sequences matter more than counts for hierarchy, and CTA counts may include navigation elements rather than conversion-focused actions.

- **Scraped content is treated as untrusted input.** Page text is provided as data only. Instructions embedded inside webpages are not followed and may themselves be reported as suspicious content.

- **Long pages are truncated instead of summarized.** This avoids an additional model call and keeps the original page text available for analysis. The trade-off is that very long pages may provide incomplete context.

- **Retries are limited to recoverable failures.** Temporary network issues, server errors, and invalid model output can retry. Quota exhaustion fails immediately because waiting will not resolve it.

## Limitations

- **No JavaScript rendering.** The scraper uses plain HTTP requests, so JS-heavy pages and bot-protection pages may not contain enough content to audit.

- **CTA detection is heuristic.** It detects common CTA patterns but may miss visually styled buttons that lack semantic HTML markers.

- **Hidden content detection is limited to static HTML.** It detects common hidden elements such as `display:none`, but cannot determine whether hidden sections are legitimate UI components or SEO manipulation.

- **Chrome removal depends on semantic HTML.** Standard `<nav>`, `<header>`, and `<footer>` sections are removed before analysis, but custom layouts using generic containers may not be detected.

## Validation

Every metric was cross-checked against a large real page (565KB HTML, 1200+ links) by independently
re-implementing each metric definition and diffing the results; all fields matched exactly.

The 45-test suite covers both halves of the tool, not just the scraper. Scraper coverage: heading
order, link normalization and deduplication, non-navigational link schemes, missing versus decorative
alt text, chrome exclusion, text extraction, and network failure modes (timeouts, non-2xx, non-HTML).
AI layer and API coverage: the retry policy (which errors retry, which don't, and the `429`
fail-fast rule), prompt construction and truncation, the orchestrator's scrape-then-analyze wiring,
and the `/audit` route's error-code mapping. All AI calls are mocked; no test hits the real Gemini
API.

## Future improvements

- **Verify citations in code.** Grounding is currently enforced only by the prompt; nothing checks a citation against the actual metrics.
  - *Detecting* a mismatch is cheap: every citation is already `"field_name: value"`, so validation is just a lookup and comparison.
  - *Fixing* a mismatch requires re-calling the model with the discrepancy as feedback, doubling the request cost against the free-tier quota. Exact matching should also be done carefully without wasting API calls.

- **Validate prompt injection in code, not just in the prompt.** The current defense is a system-prompt rule telling the model to treat page content as data rather than instructions. Since the tool audits arbitrary third-party webpages, a malicious page can deliberately include prompt-injection attempts. A more robust approach would scan scraped content for known injection patterns before it reaches the model and flag outputs that look suspiciously influenced, rather than relying solely on prompt instructions.

- **Split the audit into two passes:** generate insights first, then recommendations conditioned on those insights instead of producing both in a single call. This should improve recommendation quality, at twice the request cost.

- **Summarize very long pages before auditing them**, if truncation proves to be a practical limitation. A larger-context model could first compress the page, with the existing model auditing that summary instead of a truncated slice. This would need to remain compatible with the project's free-tier constraint, and the loss of detail would need validation against real pages.

- **Adversarial self-review pass.** A second model call would receive the metrics and generated insights and be asked only to identify claims that aren't supported by the evidence.

- **Cache audit results.** If the same website is audited again, reuse the previous result instead of scraping the page and calling the model again. This reduces latency, conserves API quota, and avoids repeated work for unchanged pages. If a paid API key is configured, automatically use a stronger model instead of the default free-tier Flash model.

- **Headless-browser fallback for JS-rendered pages.** The scraper currently uses a plain HTTP client, so JavaScript-rendered pages and bot-protection interstitials often contain little or no useful content. Falling back to a headless browser (e.g. Playwright) when a page appears empty or fails to fetch would significantly improve coverage, at the cost of additional dependencies, latency, and resource usage.

- **Smarter 429 handling.** Gemini distinguishes temporary rate limiting from daily quota exhaustion. Retrying only temporary throttling while failing fast on exhausted daily quotas would improve reliability without unnecessary retries.

- **SSRF hardening and response size limits.** The current implementation fetches any user-supplied URL without restricting destination IPs or limiting response size. Before deployment as a public service, it should restrict requests to safe destinations and enforce a maximum response size.