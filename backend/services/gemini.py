"""
Vertex AI / Gemini wrapper service.
Single place to change model, temperature, retry logic.
"""
import json
import logging
import re

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

log = logging.getLogger("rca.gemini")

_model: GenerativeModel | None = None


def init_gemini(project: str, location: str, model_name: str) -> None:
    global _model
    vertexai.init(project=project, location=location)
    _model = GenerativeModel(model_name)
    log.info("Gemini initialised  model=%s  project=%s  location=%s",
             model_name, project, location)


async def call_gemini(prompt: str, max_tokens: int = 4096) -> str:
    """Call Gemini and return the raw text response."""
    if _model is None:
        raise RuntimeError("Gemini not initialised — call init_gemini() first")

    cfg = GenerationConfig(
        max_output_tokens=max_tokens,
        temperature=0.2,
        top_p=0.8,
    )
    log.info("Gemini call  prompt_len=%d  max_tokens=%d", len(prompt), max_tokens)
    resp = await _model.generate_content_async(prompt, generation_config=cfg)
    text = resp.text
    log.info("Gemini response  len=%d", len(text))
    return text


async def call_gemini_json(prompt: str, max_tokens: int = 4096) -> dict:
    """
    Call Gemini expecting a JSON response.
    Strips markdown fences, extracts first JSON object/array, and parses.
    Retries up to 3 times with increasing max_tokens if JSON is truncated.
    Raises ValueError on bad JSON or if the result is not a dict.
    """
    import asyncio
    last_error = None
    token_steps = [max_tokens, max_tokens + 2048, max_tokens + 4096]

    for attempt, tokens in enumerate(token_steps):
        raw = await call_gemini(prompt, tokens)

        # Strip ```json ... ``` fences if present
        clean = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
        clean = re.sub(r"\s*```$", "", clean).strip()

        # If there's surrounding text, extract the first {...} or [...] block
        match = re.search(r"(\{.*\}|\[.*\])", clean, re.DOTALL)
        if match:
            clean = match.group(1)

        try:
            parsed = json.loads(clean)
        except json.JSONDecodeError as e:
            last_error = e
            log.warning("JSON parse failed attempt=%d tokens=%d error=%s raw_tail=%s",
                        attempt + 1, tokens, e, raw[-200:])
            if attempt < len(token_steps) - 1:
                await asyncio.sleep(1)
                continue
            log.error("All retries exhausted. raw=%s", raw[:500])
            raise ValueError(f"Gemini did not return valid JSON: {e}") from e

        # Guard against double-encoded JSON (Gemini returning a JSON string)
        if isinstance(parsed, str):
            try:
                parsed = json.loads(parsed)
            except json.JSONDecodeError as e:
                raise ValueError(f"Gemini returned a double-encoded JSON string: {e}") from e

        if not isinstance(parsed, dict):
            log.error("Expected dict from Gemini, got %s: %s", type(parsed).__name__, str(parsed)[:300])
            raise ValueError(f"Gemini returned {type(parsed).__name__} instead of a JSON object")

        return parsed

    raise ValueError(f"Gemini did not return valid JSON after retries: {last_error}")
