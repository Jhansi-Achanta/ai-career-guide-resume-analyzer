"""Wrapper around the Gemini API using the current ``google-genai`` SDK.

Design notes
------------
* The API key is read from ``.env`` through :mod:`config` and stays on the
  server.  The browser only ever calls our own Flask JSON API.
* Two failures matter to users, so they get their own exception types:
  :class:`AINotConfiguredError` (no key in ``.env``) and
  :class:`AIRequestError` (an already-friendly API failure message).
* Temporary Gemini server problems are retried a couple of times with a short
  backoff. Rate limits are returned immediately so a retry cannot amplify them.
"""

from __future__ import annotations

import json
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from google import genai
from google.genai import errors, types

import config


class AINotConfiguredError(RuntimeError):
    """Raised when ``GEMINI_API_KEY`` is missing from the ``.env`` file."""


class AIRequestError(RuntimeError):
    """An AI failure whose message is already safe to show to the user."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Client management
# ---------------------------------------------------------------------------
_client: Optional[genai.Client] = None
_client_lock = threading.Lock()

# Existing backoff for temporary errors other than HTTP 503.
_RETRY_DELAYS = (0.0, 1.5, 3.0)
# HTTP 503 high-demand backoff: at most three total attempts.
_SERVICE_UNAVAILABLE_RETRY_DELAYS = (0.0, 2.0, 4.0)
_RETRYABLE_STATUS_CODES = {408, 500, 502, 503, 504}


def is_configured() -> bool:
    return config.AI_CONFIGURED


def get_client() -> "genai.Client":
    """Create (once) and return a Gemini client."""
    global _client

    if not config.AI_CONFIGURED:
        raise AINotConfiguredError(
            "The Gemini API key is not set. Open the '.env' file in the project "
            "folder, add your key after GEMINI_API_KEY=, save the file and "
            "restart the server."
        )

    if _client is None:
        with _client_lock:
            if _client is None:
                _client = genai.Client(
                    api_key=config.GEMINI_API_KEY,
                    http_options=types.HttpOptions(
                        retry_options=types.HttpRetryOptions(attempts=1)
                    ),
                )
    return _client


# ---------------------------------------------------------------------------
# Retry + error translation
# ---------------------------------------------------------------------------
def _run_with_retry(operation: Callable[[], Any]) -> Any:
    """Run ``operation``, retrying temporary Gemini failures."""
    last_error: Optional[Exception] = None

    for attempt, delay in enumerate(_RETRY_DELAYS):
        if attempt and _code_of(last_error) == 503:
            delay = _SERVICE_UNAVAILABLE_RETRY_DELAYS[attempt]
        if delay:
            time.sleep(delay)
        try:
            return operation()
        except errors.ServerError as exc:  # temporary 5xx - retry
            last_error = exc
        except errors.ClientError as exc:  # 4xx - only some are retryable
            if _code_of(exc) in _RETRYABLE_STATUS_CODES:
                last_error = exc
            else:
                raise _translate_error(exc) from exc
        except errors.APIError as exc:  # preserve retries for other SDK failures
            if _code_of(exc) == 429:
                raise _translate_error(exc) from exc
            last_error = exc
        except Exception as exc:  # Interactions API uses a separate error hierarchy
            if _code_of(exc) in _RETRYABLE_STATUS_CODES:
                last_error = exc
            else:
                raise _translate_error(exc) from exc

    raise _translate_error(last_error) from last_error


def _code_of(exc: Optional[Exception]) -> Optional[int]:
    if exc is None:
        return None
    for code in (
        getattr(exc, "code", None),
        getattr(exc, "status_code", None),
        getattr(getattr(exc, "response", None), "status_code", None),
    ):
        if code is None:
            continue
        try:
            return int(code)
        except (TypeError, ValueError):
            continue
    return None


def _redact(text: str) -> str:
    """Guarantee the API key can never appear in a response or a log line."""
    key = config.GEMINI_API_KEY
    if key and key in text:
        text = text.replace(key, "<redacted>")
    return text


def _translate_error(exc: Optional[Exception]) -> AIRequestError:
    """Convert an SDK error into a message a student can act on."""
    if exc is None:
        return AIRequestError("Something went wrong while talking to Gemini. Please try again.")

    code = _code_of(exc)
    if code is None and type(exc).__module__.startswith(("google.genai", "httpx")):
        detail = _redact(str(getattr(exc, "message", "") or exc or "").strip())
        return AIRequestError(
            "Gemini is temporarily unavailable. Please try again in a moment.", 503
        )
    status = str(getattr(exc, "status", "") or "").upper()
    detail = str(getattr(exc, "message", "") or exc or "").strip()

    # An invalid or revoked key comes back as HTTP 400 INVALID_ARGUMENT with
    # reason API_KEY_INVALID (not 401), so it must be detected before the
    # generic 400 branch.  This signature is only used for matching - it is
    # never returned to the browser.
    signature = " ".join((status, detail, repr(getattr(exc, "details", None) or ""))).upper()

    if code in {401, 403} or "API_KEY_INVALID" in signature or "API KEY NOT VALID" in signature:
        return AIRequestError(
            "Gemini rejected the API key. Please check GEMINI_API_KEY in your '.env' file.",
            502,
        )
    if code == 404:
        return AIRequestError(
            f"The model '{config.GEMINI_MODEL}' is not available for your API key. "
            "Open '.env' and set GEMINI_MODEL to a model your key supports "
            "(you can see the list at GET /api/models).",
            502,
        )
    if code == 429:
        return AIRequestError(
            "Gemini is rate-limiting requests right now. Please wait a few seconds "
            "and try again.",
            429,
        )
    if code == 400:
        return AIRequestError(
            "Gemini could not process this request. Please check your input and try again.",
            502,
        )
    if code in {500, 502, 503, 504}:
        return AIRequestError(
            "Gemini is temporarily unavailable. Please try again in a moment.",
            503,
        )

    suffix = f" ({code})" if code else ""
    trimmed = f": {detail[:180]}" if detail else ""
    return AIRequestError(_redact(f"The AI request failed{suffix}{trimmed}"), 502)


# ---------------------------------------------------------------------------
# Public generation helpers
# ---------------------------------------------------------------------------
def generate_json(
    prompt: str,
    schema: Dict[str, Any],
    system_instruction: str,
    temperature: float = 0.4,
) -> Dict[str, Any]:
    """Ask Gemini for JSON text, parse it, and validate required fields."""
    client = get_client()
    input_text = (
        f"{prompt}\n\n"
        "Return only one valid JSON object. Do not use markdown fences. "
        "Include every required field and follow this schema:\n"
        f"{json.dumps(schema, ensure_ascii=False)}"
    )

    def operation() -> Any:
        return client.interactions.create(
            model=config.GEMINI_MODEL,
            input=input_text,
            system_instruction=system_instruction,
            generation_config={"temperature": temperature},
            store=False,
            timeout=45,
        )

    response = _run_with_retry(operation)
    data = _parse_json(_response_text(response))

    if not isinstance(data, dict):
        raise AIRequestError(
            "Gemini returned an unexpected response format. Please try again.", 502
        )
    _validate_required_fields(data, schema)
    return data


def list_available_models() -> List[str]:
    """Names of the models this API key can use (handy for troubleshooting)."""
    client = get_client()

    def operation() -> List[Any]:
        return list(client.models.list())

    models = _run_with_retry(operation)
    names: List[str] = []
    for model in models:
        name = str(getattr(model, "name", "") or "")
        if name.startswith("models/"):
            name = name[len("models/") :]
        if name:
            names.append(name)
    return names


# ---------------------------------------------------------------------------
# Response handling
# ---------------------------------------------------------------------------
def _response_text(response: Any) -> str:
    """Pull the text out of a Gemini response, with a manual fallback."""
    if response is None:
        raise AIRequestError("Gemini returned no response. Please try again.", 502)

    for attribute in ("output_text", "text"):
        try:
            text = getattr(response, attribute, None)
        except Exception:
            text = None
        if isinstance(text, str) and text.strip():
            return text.strip()

    # Interactions API responses contain message items with text content blocks.
    output = getattr(response, "output", None) or []
    collected = []
    for item in output:
        content = getattr(item, "content", None) or []
        for part in content:
            part_text = getattr(part, "text", None)
            if isinstance(part_text, str) and part_text:
                collected.append(part_text)

    joined = "".join(collected).strip()
    if joined:
        return joined

    # Fallback: join the parts ourselves (multi-part replies, some SDK setups).
    collected = []
    for candidate in getattr(response, "candidates", None) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", None) or []:
            part_text = getattr(part, "text", None)
            if part_text:
                collected.append(part_text)

    joined = "".join(collected).strip()
    if joined:
        return joined

    if _was_blocked(response):
        raise AIRequestError(
            "Gemini declined to answer this request, most likely because of the "
            "content that was submitted. Please review your input and try again.",
            422,
        )

    raise AIRequestError("Gemini returned an empty response. Please try again.", 502)


def _validate_required_fields(data: Any, schema: Dict[str, Any]) -> None:
    """Check required object fields throughout a parsed schema-shaped result."""
    schema_type = schema.get("type")
    if schema_type == "object":
        if not isinstance(data, dict):
            raise AIRequestError(
                "Gemini returned an incomplete response. Please try again.", 502
            )
        missing = [key for key in schema.get("required", []) if key not in data]
        if missing:
            raise AIRequestError(
                "Gemini returned an incomplete response. Please try again.", 502
            )
        properties = schema.get("properties", {})
        for key, property_schema in properties.items():
            if key in data:
                _validate_required_fields(data[key], property_schema)
    elif schema_type == "array":
        if not isinstance(data, list):
            raise AIRequestError(
                "Gemini returned an incomplete response. Please try again.", 502
            )
        item_schema = schema.get("items", {})
        for item in data:
            _validate_required_fields(item, item_schema)


def _was_blocked(response: Any) -> bool:
    """True when the reply was stopped by a safety filter."""
    feedback = getattr(response, "prompt_feedback", None)
    if getattr(feedback, "block_reason", None):
        return True

    for candidate in getattr(response, "candidates", None) or []:
        reason = str(getattr(candidate, "finish_reason", "") or "").upper()
        if "SAFETY" in reason or "BLOCK" in reason:
            return True
    return False


def _parse_json(text: str) -> Any:
    """Parse JSON from the model, tolerating stray formatting around it."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Sometimes the reply is wrapped in a ```json fence.
    fenced = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        try:
            return json.loads(fenced.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Last resort: take the outermost {...} block.
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise AIRequestError(
        "Gemini returned a response we could not read. Please try again.", 502
    )
