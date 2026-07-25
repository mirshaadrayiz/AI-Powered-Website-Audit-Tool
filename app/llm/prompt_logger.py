import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel

logger = logging.getLogger(__name__)

LOG_DIR = Path(__file__).parent.parent.parent / "logs"


def log_call(
    *,
    system_prompt: str,
    user_prompt: str,
    schema: type[BaseModel],
    model: str,
    attempt: int,
    raw_output: str,
    parsed_output: BaseModel,
) -> Path | None:
    """
    Write one record of a successful model call to logs/, as plain text.
    """
    timestamp = datetime.now(timezone.utc)
    filename = f"{timestamp.strftime('%Y%m%dT%H%M%S')}_{uuid4().hex[:8]}.log"

    lines = [
        f"timestamp: {timestamp.isoformat()}",
        f"model: {model}",
        f"attempt: {attempt}",
        f"schema: {schema.__name__}",
        "",
        "--- SYSTEM PROMPT ---",
        system_prompt,
        "",
        "--- USER PROMPT ---",
        user_prompt,
        "",
        "--- RAW OUTPUT ---",
        raw_output,
        "",
        "--- PARSED OUTPUT ---",
        json.dumps(parsed_output.model_dump(), indent=2, ensure_ascii=False),
    ]

    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        path = LOG_DIR / filename
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path
    except OSError as exc:
        logger.warning("Could not write prompt log %s: %s", filename, exc)
        return None
