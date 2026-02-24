"""JSON schemas used by extraction and decision steps.

The agent uses strict JSON schema outputs so downstream logic can rely on
predictable keys and types.
"""

# Structured medical entities extracted from a document.
ENTITIES_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "patient_name": {"type": ["string", "null"]},
        "dob": {"type": ["string", "null"], "description": "YYYY-MM-DD"},
        "report_date": {"type": ["string", "null"], "description": "YYYY-MM-DD"},
        "provider_name": {"type": ["string", "null"]},
        "diagnoses": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "icd10": {"type": ["string", "null"]},
                },
                "required": ["name", "icd10"],
            },
        },
        "medications": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "dose": {"type": ["string", "null"]},
                    "frequency": {"type": ["string", "null"]},
                },
                "required": ["name", "dose", "frequency"],
            },
        },
        "procedures": {"type": "array", "items": {"type": "string"}},
        "key_dates": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "patient_name",
        "dob",
        "report_date",
        "provider_name",
        "diagnoses",
        "medications",
        "procedures",
        "key_dates",
    ],
}


# Data quality and completeness issues identified during extraction.
ISSUES_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "missing_fields": {"type": "array", "items": {"type": "string"}},
        "missing_numerical_values": {"type": "array", "items": {"type": "string"}},
        "data_quality_flags": {"type": "array", "items": {"type": "string"}},
        "confidence_notes": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "missing_fields",
        "missing_numerical_values",
        "data_quality_flags",
        "confidence_notes",
    ],
}


# Top-level extraction payload: summary + entities + issues.
EXTRACTION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary_bullets": {"type": "array", "items": {"type": "string"}},
        "entities": ENTITIES_SCHEMA,
        "issues": ISSUES_SCHEMA,
    },
    "required": ["summary_bullets", "entities", "issues"],
}


# Final underwriting recommendation payload.
DECISION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "decision": {
            "type": "string",
            "enum": ["APPROVE", "REQUEST_DOCUMENTS", "REFER_UNDERWRITER", "DECLINE_TRIAGE"],
        },
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "rationale": {
            "type": "string",
            "description": "2-4 sentence plain-English explanation of the decision",
        },
        "action_items": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Concrete next steps for the claims handler",
        },
        "documents_requested": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Specific documents to request if decision is REQUEST_DOCUMENTS",
        },
        "underwriter_notes": {
            "type": ["string", "null"],
            "description": "Notes for underwriter if decision is REFER_UNDERWRITER; else null",
        },
    },
    "required": [
        "decision",
        "confidence",
        "rationale",
        "action_items",
        "documents_requested",
        "underwriter_notes",
    ],
}
