"""LLM-based document extraction.

This module calls the OpenAI Responses API to transform raw claim text into:
1) summary bullets
2) structured entities
3) data-quality issues
"""

import json

from openai import OpenAI

from .ingest import pdf_to_text
from .schemas import EXTRACTION_SCHEMA


def extract_summary_and_entities(
    client: OpenAI,
    model: str,
    source: str,
    source_type: str = "text",
) -> dict:
    """Extract summary, entities, and issues from text or PDF input.

    Args:
        client: Initialized OpenAI client.
        model: Model name for the extraction call.
        source: Raw text or PDF file path.
        source_type: Either "text" or "pdf".

    Returns:
        A dictionary matching ``EXTRACTION_SCHEMA``.
    """
    if source_type == "pdf":
        text = pdf_to_text(source)
        if not text.strip():
            return {"error": "No text could be extracted. PDF may be scanned/image-based."}
    else:
        text = source

    resp = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "You extract structured data from medical documents for life insurance triage.\n"
                    "Rules:\n"
                    "- Be factual. Never invent data.\n"
                    "- Missing fields -> null or empty list.\n"
                    "- Dates -> YYYY-MM-DD. Year only -> 'YYYY'. Year+month -> 'YYYY-MM'.\n"
                    "- Flag 'relative_date_present' when relative time appears.\n"
                    "- Flag 'year_only_dates_present' if any date is year-only.\n"
                ),
            },
            {
                "role": "user",
                "content": (
                    "1) Write 6-10 concise bullet-point summary of the document.\n"
                    "2) Extract entities.\n"
                    "3) Identify issues: missing_fields, missing_numerical_values, "
                    "data_quality_flags, confidence_notes.\n\n"
                    f"DOCUMENT:\n{text}"
                ),
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "extraction",
                "schema": EXTRACTION_SCHEMA,
                "strict": True,
            }
        },
    )
    return json.loads(resp.output_text)
