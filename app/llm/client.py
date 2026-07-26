import asyncio
from functools import lru_cache

import httpx
from google import genai
from google.genai import types
from google.genai.errors import APIError
from pydantic import BaseModel, ValidationError

from app.llm.prompt_logger import log_call
from app.config import settings

REQUEST_TIMEOUT_MS = 60_000
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 1.0
RETRYABLE_STATUS_CODES = {408, 500, 502, 503, 504}
TEMPERATURE = 0.0
MAX_OUTPUT_TOKENS = 4096


class AIError(Exception):
    """Raised when the model call fails after all retry attempts are exhausted."""


@lru_cache
def _client() -> genai.Client:
    return genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS),
    )


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return True
    if isinstance(exc, APIError):
        return exc.code in RETRYABLE_STATUS_CODES
    return isinstance(exc, ValidationError)


async def generate_structured(system_prompt: str, user_prompt: str, schema: type[BaseModel]) -> tuple[str, BaseModel]:
    """Call Gemini with a forced JSON schema and return (raw_text, parsed_instance).

    Retries timeouts, connection errors, 408/5xx responses, and
    schema-violating output up to MAX_ATTEMPTS with exponential backoff, so a
    single bad response or transient upstream hiccup doesn't fail the whole
    audit. 429s are not retried since on a rate-limited free-tier quota a
    retry has no chance of succeeding before the quota resets.
    """
    attempt = 0
    while True:
        attempt += 1
        raw_text: str | None = None
        try:
            response = await _client().aio.models.generate_content(
                model=settings.gemini_model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    response_json_schema=schema.model_json_schema(),
                    temperature=TEMPERATURE,
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                ),
            )
            raw_text = response.text
            parsed = schema.model_validate_json(raw_text)
        except Exception as exc:
            if attempt < MAX_ATTEMPTS and _is_retryable(exc):
                await asyncio.sleep(RETRY_BACKOFF_SECONDS * 2 ** (attempt - 1))
                continue
            raise AIError(f"Gemini call failed after {attempt} attempt(s): {exc}") from exc
        else:
            log_call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=schema,
                model=settings.gemini_model,
                attempt=attempt,
                raw_output=raw_text,
                parsed_output=parsed,
            )
            return raw_text, parsed