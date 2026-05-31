import asyncio
import time
import logging
from google import genai
from google.genai import types
from app.config import GEMINI_API_KEY, GEN_MODEL, EMBED_MODEL, EMBED_DIM

logger = logging.getLogger(__name__)

client = genai.Client(api_key=GEMINI_API_KEY)

_MAX_RETRIES = 4
_BASE_DELAY = 2.0


def _retry_on_429(fn, *args, **kwargs):
    delay = _BASE_DELAY
    for attempt in range(_MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            msg = str(e)
            if "429" in msg or "quota" in msg.lower() or "rate" in msg.lower():
                if attempt < _MAX_RETRIES - 1:
                    logger.warning(f"Rate limit hit, retrying in {delay}s (attempt {attempt+1})")
                    time.sleep(delay)
                    delay *= 2
                else:
                    raise
            else:
                raise


def safe_generate(prompt: str, **config_kwargs) -> str:
    def _call():
        cfg = types.GenerateContentConfig(**config_kwargs) if config_kwargs else None
        resp = client.models.generate_content(
            model=GEN_MODEL,
            contents=prompt,
            config=cfg,
        )
        return resp.text

    return _retry_on_429(_call)


def safe_generate_with_parts(parts: list, **config_kwargs) -> str:
    def _call():
        cfg = types.GenerateContentConfig(**config_kwargs) if config_kwargs else None
        resp = client.models.generate_content(
            model=GEN_MODEL,
            contents=parts,
            config=cfg,
        )
        return resp.text

    return _retry_on_429(_call)


def safe_embed(texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list:
    def _call():
        result = client.models.embed_content(
            model=EMBED_MODEL,
            contents=texts,
            config=types.EmbedContentConfig(
                output_dimensionality=EMBED_DIM,
                task_type=task_type,
            ),
        )
        return result.embeddings

    return _retry_on_429(_call)
