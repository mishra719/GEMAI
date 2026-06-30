"""
AI service layer powered by OpenRouter for chat/coding plus image fallbacks.
"""
import json
import logging
import re
import uuid
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Image fallback endpoint when direct image generation is unavailable
POLLINATIONS_BASE_URL = "https://image.pollinations.ai/prompt"

# Image storage directory
IMAGES_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)


# ---------- System Prompts ----------

GENERAL_SYSTEM_PROMPT = """You are Gem-AI, a helpful, knowledgeable, and friendly AI assistant.
Provide clear, accurate, and well-structured responses.
Use markdown formatting when appropriate for readability.
Be concise but thorough."""

CODING_SYSTEM_PROMPT = """You are Gem-AI in Coding Mode — an expert software engineer.
Respond with ONLY a valid JSON object that represents the requested coding output.

The JSON must follow this exact structure:
{
  "project_name": "my-project",
  "files": {
    "path/to/file1.py": "file content here...",
    "path/to/file2.js": "file content here...",
    "README.md": "# Project\\n\\nDescription..."
  }
}

Rules:
- Return ONLY the JSON object, no markdown code blocks, no explanation before or after
- Every file path should be relative to the project root
- Include ALL necessary files for a working project
- Include a README.md with setup instructions
- Write production-quality, well-commented code
- Include proper error handling in all code
- Include a requirements.txt or package.json as needed
- Prefer the latest stable ecosystem choices and modern project structure unless the user explicitly asks for something older
- Avoid deprecated or legacy tools, packages, APIs, and patterns
- For React projects, prefer Vite-based setups over create-react-app/react-scripts unless the user explicitly requests CRA
- Choose current stable package versions that work well together and pin them in the generated manifest files
- Use modern framework conventions (for example current React patterns, modern TypeScript configs, and current routing/build defaults)"""

IMAGE_SYSTEM_PROMPT = """You are Gem-AI in Image Mode.
Generate images based on user requests. Be creative and detailed."""

CODING_RESPONSE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "project_name": {"type": "string"},
        "files": {
            "type": "object",
            "additionalProperties": {"type": "string"},
        },
    },
    "required": ["project_name", "files"],
}


# ---------- OpenRouter Helpers ----------

class OpenRouterAPIError(RuntimeError):
    """Structured OpenRouter API failure."""

    def __init__(self, status_code: int, body: str, payload: Optional[dict] = None):
        super().__init__(f"OpenRouter API error ({status_code}): {body}")
        self.status_code = status_code
        self.body = body
        self.payload = payload or {}


def _parse_csv(value: Optional[str]) -> list[str]:
    """Parse a comma-separated provider/model list."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]

def _build_messages(
    history: list[dict],
    user_message: str,
    system_prompt: str,
    max_history: int,
) -> list[dict]:
    """Build an OpenAI-compatible message list for OpenRouter."""
    messages = [{"role": "system", "content": system_prompt}]

    for msg in history[-max_history:]:
        role = "user" if msg["role"] == "user" else "assistant"
        messages.append({"role": role, "content": msg["content"]})

    messages.append({"role": "user", "content": user_message})
    return messages


def _openrouter_headers() -> dict[str, str]:
    """Build request headers for OpenRouter."""
    if not settings.OPENROUTER_API_KEY:
        raise RuntimeError("OpenRouter API key is missing.")

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    if settings.OPENROUTER_HTTP_REFERER:
        headers["HTTP-Referer"] = settings.OPENROUTER_HTTP_REFERER
    if settings.OPENROUTER_APP_TITLE:
        headers["X-Title"] = settings.OPENROUTER_APP_TITLE

    return headers


def _extract_message_text(content) -> str:
    """Normalize OpenRouter/OpenAI-style message content into plain text."""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                text_parts.append(part)
                continue

            if isinstance(part, dict):
                if isinstance(part.get("text"), str):
                    text_parts.append(part["text"])
                elif isinstance(part.get("content"), str):
                    text_parts.append(part["content"])

        return "".join(text_parts).strip()

    return ""


def _build_provider_preferences(
    only: Optional[list[str]] = None,
    require_parameters: bool = False,
) -> Optional[dict]:
    """Build a provider preferences object for OpenRouter."""
    provider: dict[str, object] = {}
    if only:
        provider["only"] = only
    if require_parameters:
        provider["require_parameters"] = True
    return provider or None


def _available_providers_from_error(exc: Exception) -> list[str]:
    """Extract OpenRouter's suggested available providers from an API error."""
    if not isinstance(exc, OpenRouterAPIError):
        return []

    metadata = exc.payload.get("error", {}).get("metadata", {})
    available = metadata.get("available_providers") or []
    return [provider for provider in available if isinstance(provider, str) and provider.strip()]


def _should_use_free_fallback(exc: Exception) -> bool:
    """Detect errors that should fall back to the free router."""
    error_text = str(exc).lower()
    rate_limit_markers = (
        "429",
        "rate-limit",
        "rate limited",
        "temporarily rate-limited upstream",
    )
    provider_markers = (
        "no allowed providers are available",
        "provider returned error",
    )
    return any(marker in error_text for marker in rate_limit_markers + provider_markers)


def _openrouter_chat_completion(
    model: str,
    messages: list[dict],
    response_format: Optional[dict] = None,
    provider: Optional[dict] = None,
) -> str:
    """Call OpenRouter's chat completions API and return the first message text."""
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": settings.OPENROUTER_MAX_TOKENS,
    }

    if response_format:
        payload["response_format"] = response_format
        provider = {
            **(provider or {}),
            "require_parameters": True,
        }

    if provider:
        payload["provider"] = provider

    request = urllib.request.Request(
        settings.OPENROUTER_BASE_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=_openrouter_headers(),
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=settings.OPENROUTER_TIMEOUT_SECONDS,
        ) as response:
            raw_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        try:
            error_payload = json.loads(error_body)
        except json.JSONDecodeError:
            error_payload = {}
        raise OpenRouterAPIError(exc.code, error_body, error_payload) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Unable to reach OpenRouter: {exc.reason}") from exc

    try:
        response_data = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise RuntimeError("OpenRouter returned invalid JSON.") from exc

    if response_data.get("error"):
        raise RuntimeError(f"OpenRouter API error: {response_data['error']}")

    choices = response_data.get("choices") or []
    if not choices:
        raise RuntimeError("OpenRouter returned no choices.")

    message = choices[0].get("message") or {}
    content = _extract_message_text(message.get("content"))
    if not content:
        raise RuntimeError("OpenRouter returned an empty response.")

    return content


def _should_retry_without_schema(exc: Exception) -> bool:
    """Detect structured-output compatibility failures and retry without schema."""
    error_text = str(exc).lower()
    markers = (
        "response_format",
        "json_schema",
        "structured output",
        "unsupported parameter",
        "require_parameters",
        "does not support",
        "requested parameters",
        "no endpoints found that can handle the requested parameters",
    )
    return any(marker in error_text for marker in markers)


def _request_with_provider_recovery(
    model: str,
    messages: list[dict],
    response_format: Optional[dict] = None,
    provider: Optional[dict] = None,
) -> str:
    """Retry once with explicitly allowed providers if OpenRouter exposes them."""
    try:
        return _openrouter_chat_completion(
            model=model,
            messages=messages,
            response_format=response_format,
            provider=provider,
        )
    except Exception as exc:
        available_providers = _available_providers_from_error(exc)
        if not available_providers:
            raise

        logger.warning(
            "Retrying %s with OpenRouter available providers: %s",
            model,
            ", ".join(available_providers),
        )
        merged_provider = {
            **(provider or {}),
            "only": available_providers,
        }
        return _openrouter_chat_completion(
            model=model,
            messages=messages,
            response_format=response_format,
            provider=merged_provider,
        )


def _request_with_free_fallback(
    primary_model: str,
    messages: list[dict],
    response_format: Optional[dict] = None,
) -> str:
    """Use the primary model first, then fall back to OpenRouter's free router if needed."""
    try:
        return _request_with_provider_recovery(
            model=primary_model,
            messages=messages,
            response_format=response_format,
        )
    except Exception as primary_error:
        if not _should_use_free_fallback(primary_error):
            raise

        logger.warning(
            "Primary model %s failed, retrying with %s: %s",
            primary_model,
            settings.OPENROUTER_FREE_FALLBACK_MODEL,
            primary_error,
        )

        fallback_candidates: list[tuple[str, list[str]]] = [
            (
                settings.OPENROUTER_FREE_FALLBACK_MODEL,
                _parse_csv(settings.OPENROUTER_FALLBACK_PROVIDERS),
            ),
            ("google/gemma-3-12b-it:free", ["google-ai-studio"]),
            ("openrouter/free", ["nvidia"]),
        ]

        last_error: Optional[Exception] = None
        for fallback_model, provider_slugs in fallback_candidates:
            for provider_slug in provider_slugs or [None]:
                try:
                    logger.warning(
                        "Trying fallback model %s via provider %s",
                        fallback_model,
                        provider_slug or "auto",
                    )
                    return _request_with_provider_recovery(
                        model=fallback_model,
                        messages=messages,
                        response_format=response_format,
                        provider=_build_provider_preferences(
                            only=[provider_slug] if provider_slug else None,
                            require_parameters=bool(response_format),
                        ),
                    )
                except Exception as provider_error:
                    last_error = provider_error
                    logger.warning(
                        "Fallback provider %s failed for %s: %s",
                        provider_slug or "auto",
                        fallback_model,
                        provider_error,
                    )

        if last_error is not None:
            raise last_error
        raise primary_error


def _extract_json_candidate(response_text: str) -> str:
    """Extract the most likely JSON payload from a model response."""
    if not response_text:
        return ""

    direct_text = response_text.strip()
    if direct_text.startswith("{") and direct_text.endswith("}"):
        return direct_text

    if direct_text.startswith("```"):
        first_newline = direct_text.find("\n")
        if first_newline != -1:
            fenced_body = direct_text[first_newline + 1:]
            last_fence = fenced_body.rfind("```")
            if last_fence != -1:
                return fenced_body[:last_fence].strip()

    json_match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", response_text)
    if json_match:
        return json_match.group(1).strip()

    json_match = re.search(r"\{[\s\S]*\}", response_text)
    if json_match:
        return json_match.group(0).strip()

    return direct_text


def _decode_relaxed_json_string(raw_value: str) -> str:
    """Decode a mostly-JSON string while repairing common quote/newline mistakes."""
    sanitized: list[str] = []
    escaped = False

    for char in raw_value:
        if char == "\r":
            continue
        if char == "\n":
            sanitized.append("\\n")
            escaped = False
            continue
        if char == "\t":
            sanitized.append("\\t")
            escaped = False
            continue
        if char == '"' and not escaped:
            sanitized.append('\\"')
        else:
            sanitized.append(char)

        if char == "\\" and not escaped:
            escaped = True
        else:
            escaped = False

    return json.loads(f"\"{''.join(sanitized)}\"")


def _repair_project_response(response_text: str) -> Optional[dict]:
    """Recover project JSON when the model returns almost-valid structured output."""
    candidate = _extract_json_candidate(response_text)
    if not candidate:
        return None

    project_name_match = re.search(
        r'"project_name"\s*:\s*"(?P<name>(?:[^"\\]|\\.)*)"',
        candidate,
        re.S,
    )
    files_start_match = re.search(r'"files"\s*:\s*\{', candidate)
    if not project_name_match or not files_start_match:
        return None

    file_entry_pattern = re.compile(r'(?m)^\s{4,}"(?P<key>[^"\n]+)"\s*:\s*"')
    file_matches = list(file_entry_pattern.finditer(candidate, files_start_match.end()))
    if not file_matches:
        return None

    object_end = candidate.rfind("}")
    if object_end == -1:
        return None
    files: dict[str, str] = {}

    for index, match in enumerate(file_matches):
        key = match.group("key")
        value_start = match.end()
        next_entry_start = (
            file_matches[index + 1].start()
            if index + 1 < len(file_matches)
            else object_end
        )
        raw_value = candidate[value_start:next_entry_start].rstrip()
        raw_value = re.sub(r'"\s*(?:,\s*)?(?:\}\s*)*$', "", raw_value, count=1, flags=re.S)

        try:
            files[key] = _decode_relaxed_json_string(raw_value)
        except Exception:
            files[key] = raw_value.replace("\\n", "\n").replace('\\"', '"')

    if not files:
        return None

    project_name = json.loads(f"\"{project_name_match.group('name')}\"")
    return {
        "project_name": project_name,
        "files": files,
    }


def _save_generated_image(image_bytes: bytes, mime_type: Optional[str]) -> str:
    """Persist a generated image and return its static URL."""
    image_id = str(uuid.uuid4())
    mime_type = (mime_type or "image/png").lower()
    ext = "png"
    if "jpeg" in mime_type or "jpg" in mime_type:
        ext = "jpg"
    elif "webp" in mime_type:
        ext = "webp"

    filename = f"{image_id}.{ext}"
    filepath = IMAGES_DIR / filename
    filepath.write_bytes(image_bytes)
    logger.info("Image generated and saved: %s", filename)
    return f"/static/images/{filename}"


def _generate_image_with_pollinations(user_message: str) -> Optional[dict]:
    """Fallback to a hosted image endpoint when direct image output is unavailable."""
    encoded_prompt = urllib.parse.quote(user_message)
    url = f"{POLLINATIONS_BASE_URL}/{encoded_prompt}?width=1024&height=1024&nologo=true"

    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Gem-AI/1.0"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            image_bytes = response.read()
            mime_type = response.headers.get("Content-Type", "image/png")

        if not image_bytes:
            logger.warning("Pollinations fallback returned an empty response")
            return None

        image_url = _save_generated_image(image_bytes, mime_type)
        logger.info("Image generated through Pollinations fallback")
        return {
            "type": "image",
            "image_url": image_url,
            "content": f'Here is the image I generated for "{user_message}".',
        }

    except Exception as e:
        logger.warning("Pollinations fallback failed: %s", e)
        return None


# ---------- General Chat ----------

async def general_chat(messages: list[dict], user_message: str) -> str:
    """Handle general chat using OpenRouter."""
    try:
        request_messages = _build_messages(
            history=messages,
            user_message=user_message,
            system_prompt=GENERAL_SYSTEM_PROMPT,
            max_history=20,
        )
        response_text = _request_with_free_fallback(
            settings.OPENROUTER_GENERAL_MODEL,
            request_messages,
        )
        return response_text

    except Exception as e:
        logger.error("OpenRouter general chat error: %s", e)
        return f"I'm sorry, I encountered an error: {_friendly_error(e)}"


# ---------- Coding Chat ----------

async def coding_chat(messages: list[dict], user_message: str) -> str:
    """Handle coding requests using OpenRouter."""
    try:
        request_messages = _build_messages(
            history=messages,
            user_message=user_message,
            system_prompt=CODING_SYSTEM_PROMPT,
            max_history=10,
        )

        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "coding_project",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "project_name": {"type": "string"},
                        "files": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                        },
                    },
                    "required": ["project_name", "files"],
                    "additionalProperties": False,
                },
            },
        }

        try:
            response_text = _request_with_free_fallback(
                settings.OPENROUTER_CODING_MODEL,
                request_messages,
                response_format=response_format,
            )
        except Exception as schema_error:
            if not _should_retry_without_schema(schema_error):
                raise
            logger.warning(
                "Structured output unavailable for %s, retrying without schema: %s",
                settings.OPENROUTER_CODING_MODEL,
                schema_error,
            )
            response_text = _request_with_free_fallback(
                settings.OPENROUTER_CODING_MODEL,
                request_messages,
            )

        project_data = parse_code_response(response_text)
        if project_data:
            return json.dumps(project_data, indent=2, ensure_ascii=False)

        return response_text

    except Exception as e:
        logger.error("OpenRouter coding chat error: %s", e)
        return f"I'm sorry, I encountered an error generating code: {_friendly_error(e)}"


# ---------- Image Chat ----------

async def image_chat(user_message: str) -> dict:
    """
    Handle image generation requests.
    Tries native image generation first, falls back to text description.
    """
    result = _generate_image_with_pollinations(user_message)
    if result:
        return result

    # Strategy 2: Fallback — use the text model to describe the image
    try:
        prompt = f"""The user wants an image of: {user_message}

Since I cannot generate images right now, I'll provide a detailed creative description.
Write a vivid, detailed description of what this image would look like.
Format your description beautifully with markdown. Start with a title like "🎨 Image Description" then describe the scene in detail."""

        response_text = _request_with_free_fallback(
            settings.OPENROUTER_GENERAL_MODEL,
            [
                {
                    "role": "system",
                    "content": "You are a creative AI artist. Describe images vividly and beautifully.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )

        return {
            "type": "image_description",
            "content": response_text,
        }

    except Exception as e:
        logger.error(f"Image fallback error: {e}")
        return {
            "type": "error",
            "content": f"Image generation is currently unavailable: {_friendly_error(e)}",
        }


# ---------- Parse Code Response ----------

def parse_code_response(response_text: str) -> Optional[dict]:
    """Parse the JSON project structure from the coding model response."""
    candidate = _extract_json_candidate(response_text)

    try:
        # Try direct JSON parse
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    return _repair_project_response(response_text)


# ---------- Friendly Error Message ----------

def _friendly_error(e: Exception) -> str:
    """Convert exception to a user-friendly error message."""
    error_str = str(e)
    if "429" in error_str or "rate-limit" in error_str.lower() or "rate limited" in error_str.lower():
        return "The AI service is currently rate-limited. Please wait a moment and try again."
    if "401" in error_str or "403" in error_str:
        return "API key issue. Please check your OpenRouter API key configuration."
    if "404" in error_str:
        return "The AI model is not available. Please try again later."
    if "temporarily rate-limited upstream" in error_str.lower():
        return "The selected free model is temporarily rate-limited upstream. Please retry in a moment."
    if "unable to reach openrouter" in error_str.lower():
        return "The AI service is unreachable right now. Please try again in a moment."
    return "An unexpected error occurred. Please try again."
