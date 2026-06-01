import json
import logging
from google.genai import types
from app.services.gemini_client import client, _retry_on_429
from app.config import GEN_MODEL

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = """You are a senior Indian legal advocate. Given a user's case summary and a set of retrieved legal case excerpts, assess which cases are genuinely legally similar.

USER CASE SUMMARY:
{summary}

RETRIEVED CASE EXCERPTS:
{excerpts}

Return a JSON array. Each item must have exactly these keys:
- "case_name": string (extract from text, e.g. "State of Maharashtra v. Rajesh Kumar")
- "citation": string or null (e.g. "2014 SCR 123", null if not found)
- "relevance_score": float between 0.0 and 1.0 (genuine legal similarity, not just keyword match)
- "key_overlap": array of strings (shared statutes, legal principles, or facts)
- "reasoning": string (one sentence why this case is or isn't similar)
- "source_url": string (the URL of this excerpt)

Include all cases with relevance_score >= 0.15. Return ONLY valid JSON array, no markdown."""


def validate_matches(user_case_summary: str, top_chunks: list[dict]) -> list[dict]:
    excerpts_text = ""
    for i, chunk in enumerate(top_chunks):
        excerpts_text += f"\n[{i+1}] URL: {chunk['url']}\n{chunk['text'][:800]}\n"

    prompt = _PROMPT_TEMPLATE.format(
        summary=user_case_summary,
        excerpts=excerpts_text,
    )

    def _call():
        resp = client.models.generate_content(
            model=GEN_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        return resp.text

    raw = _retry_on_429(_call)
    results = json.loads(raw)

    if not isinstance(results, list):
        results = [results]

    # Ensure all required keys exist
    required = {"case_name", "citation", "relevance_score", "key_overlap", "reasoning", "source_url"}
    validated = []
    for item in results:
        if required.issubset(item.keys()):
            item["relevance_score"] = float(item["relevance_score"])
            validated.append(item)

    validated.sort(key=lambda x: x["relevance_score"], reverse=True)
    logger.info(f"Validator returned {len(validated)} valid citations")
    return validated
