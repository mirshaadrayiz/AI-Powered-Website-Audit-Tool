from google import genai
from google.genai import types
from pydantic import BaseModel

from app.ai.prompt_logger import log_call
from app.config import settings


def generate_structured(system_prompt: str, user_prompt: str, schema: type[BaseModel]) -> tuple[str, BaseModel]:
    """Call Gemini with a forced JSON schema and return (raw_text, parsed_instance).

    response_json_schema (not the SDK's response_schema shortcut) is used
    deliberately — it accepts a full JSON schema including $defs/$ref, which
    response_schema doesn't reliably handle for nested Pydantic models.

    Every call is logged to logs/prompt_logs/ (system prompt, constructed user
    prompt, schema, raw output, parsed output) — the prompt logs deliverable,
    captured automatically rather than assembled by hand after the fact.
    """
    client = genai.Client(api_key=settings.gemini_api_key)

    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_json_schema=schema.model_json_schema(),
        ),
    )

    parsed = schema.model_validate_json(response.text)

    log_call(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        schema=schema,
        model=settings.gemini_model,
        raw_output=response.text,
        parsed_output=parsed,
    )

    return response.text, parsed


# if __name__ == "__main__":
#     # uv run -m app.ai.client

#     class Greeting(BaseModel):
#         message: str

#     raw_text, parsed = generate_structured(
#         system_prompt="You are a friendly assistant.",
#         user_prompt="Say hello in one short sentence.",
#         schema=Greeting,
#     )
#     print("Raw:", raw_text)
#     print("Parsed:", parsed)
