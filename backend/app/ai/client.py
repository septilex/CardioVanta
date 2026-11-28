"""No clinical logging or persistence; the optional SDK is loaded only on demand."""
import asyncio
import importlib.util
import json
import logging
import os
from backend.app.core.config import settings
from .schemas import ExplanationRequest, ExplanationContent, ExplanationResponse
from .prompts.explanation_v1 import SYSTEM, VERSION

class ExplanationError(Exception):
    def __init__(self, status: int, code: str):
        self.status, self.code = status, code

def available() -> bool:
    shared_controls = settings.REDIS_URL or (not os.getenv("VERCEL") and settings.ENVIRONMENT == "development" and settings.AI_USAGE_DB)
    return bool(shared_controls and settings.AI_SIGNING_KEY and len(settings.AI_SIGNING_KEY.get_secret_value()) >= 32 and settings.LLM_ENABLED and settings.OPENAI_API_KEY and settings.OPENAI_MODEL.strip()
                and importlib.util.find_spec("openai"))

async def provider_parse(data: ExplanationRequest):
    from openai import AsyncOpenAI
    # SDK debug logging may contain request bodies; never emit it here.
    logging.getLogger("openai._base_client").disabled = True
    # Explicit destination, bounded timeout, no automatic repeated paid requests.
    async with AsyncOpenAI(api_key=settings.require_secret("OPENAI_API_KEY"),
                           base_url="https://api.openai.com/v1", timeout=20, max_retries=0) as client:
        return await client.chat.completions.parse(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "system", "content": SYSTEM},
                      {"role": "user", "content": json.dumps(data.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))}],
            response_format=ExplanationContent, max_completion_tokens=1800, store=False)

async def explain(data: ExplanationRequest) -> ExplanationResponse:
    if not available():
        raise ExplanationError(503, "AI_UNAVAILABLE")
    try:
        completion = await asyncio.wait_for(provider_parse(data), timeout=25)
        choice = completion.choices[0]
        if choice.finish_reason != "stop" or choice.message.refusal or choice.message.parsed is None:
            raise ExplanationError(502, "AI_INVALID_RESPONSE")
        content = ExplanationContent.model_validate(choice.message.parsed.model_dump())
        expected = [(f.feature_name, f.contribution_direction) for f in data.contributing_factors]
        actual = [(f.feature_name, f.contribution_direction) for f in content.contributing_factors]
        if actual != expected:
            raise ExplanationError(502, "AI_INVALID_RESPONSE")
        return ExplanationResponse(**content.model_dump(),
            recommended_next_step="Discuss personal medical decisions with a qualified healthcare professional.",
            disclaimer="AI-generated educational explanation. Not a diagnosis or a substitute for professional medical advice.",
            prompt_version=VERSION)
    except ExplanationError:
        raise
    except Exception as exc:
        # Never log, stringify or return provider exception payloads.
        from openai import APITimeoutError, RateLimitError, AuthenticationError, APIConnectionError
        if isinstance(exc, (TimeoutError, APITimeoutError)):
            raise ExplanationError(504, "AI_TIMEOUT") from None
        if isinstance(exc, RateLimitError):
            raise ExplanationError(429, "AI_RATE_LIMITED") from None
        if isinstance(exc, (AuthenticationError, APIConnectionError)):
            raise ExplanationError(503, "AI_UNAVAILABLE") from None
        raise ExplanationError(502, "AI_INVALID_RESPONSE") from None
