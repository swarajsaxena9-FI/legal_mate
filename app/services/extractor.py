import json
import logging
from google.genai import types
from app.services.gemini_client import client, _retry_on_429
from app.config import GEN_MODEL

logger = logging.getLogger(__name__)

_SCHEMA_PROMPT = """You are a legal analyst specializing in Indian court cases.
Analyze the provided case document and return a JSON object with exactly these keys:
{
  "case_summary": "2-3 line summary of the case",
  "case_type": "one of: criminal_appeal, civil_suit, cheque_bounce, writ_petition, arbitration, other",
  "statutes": ["list of relevant statutes and sections e.g. Section 138 NI Act"],
  "keywords": ["list of 5-8 key legal terms and facts"],
  "search_queries": [
    "optimized query 1 for Indian legal search including statute + court + facts",
    "optimized query 2",
    "optimized query 3"
  ]
}
Return ONLY valid JSON, no markdown, no explanation."""


def extract_legal_query(
    file_bytes: bytes | None = None,
    raw_text: str | None = None,
    mime_type: str | None = None,
) -> dict:
    def _call():
        if file_bytes is not None:
            parts = [
                types.Part.from_bytes(
                    data=file_bytes,
                    mime_type=mime_type or "application/pdf",
                ),
                _SCHEMA_PROMPT,
            ]
        else:
            parts = [raw_text, _SCHEMA_PROMPT]

        resp = client.models.generate_content(
            model=GEN_MODEL,
            contents=parts,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        return resp.text

    raw = _retry_on_429(_call)
    result = json.loads(raw)
    logger.info(f"Extracted legal query: case_type={result.get('case_type')}")
    return result
