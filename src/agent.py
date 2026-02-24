"""Agent orchestrator for life insurance claim triage.

This module defines:
1) The final decision tool call (`make_decision`)
2) Tool definitions exposed to the LLM
3) The agent loop (`run_claims_agent`) that executes tool calls and feeds
   outputs back to the model until completion.
"""

import json
from typing import Optional

from openai import OpenAI

from .extractor import extract_summary_and_entities
from .rules import assess_medical_risk, check_completeness
from .schemas import DECISION_SCHEMA


DEFAULT_MODEL = "gpt-4.1-mini"


def make_decision(
    client: OpenAI,
    model: str,
    completeness: dict,
    medical_risk: dict,
    issues: dict,
    entities: dict,
) -> dict:
    """Generate the final structured triage decision.

    Args:
        client: Initialized OpenAI client.
        model: Model name for this decision call.
        completeness: Output from completeness rules.
        medical_risk: Output from risk rules.
        issues: Data quality issues from extraction.
        entities: Extracted entities from the document.

    Returns:
        Decision object matching ``DECISION_SCHEMA``.
    """
    context = {
        "completeness_report": completeness,
        "medical_risk_report": medical_risk,
        "data_issues": issues,
        "patient_summary": {
            "name": entities.get("patient_name"),
            "dob": entities.get("dob"),
            "diagnoses": [d["name"] for d in entities.get("diagnoses", [])],
        },
    }

    resp = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "You are a senior life insurance claims assessor.\n"
                    "You receive structured assessment inputs and produce a clear, defensible decision.\n"
                    "Decision rules:\n"
                    "  APPROVE            -> All mandatory fields present AND risk_level is 'low'.\n"
                    "  REQUEST_DOCUMENTS  -> Mandatory fields missing. List exactly which docs are needed.\n"
                    "  REFER_UNDERWRITER  -> risk_level is 'high' or 'refer_to_underwriter'.\n"
                    "  DECLINE_TRIAGE     -> Cannot assess at all (e.g., extraction completely failed).\n"
                    "Be concise. Be specific. Never invent clinical facts.\n"
                ),
            },
            {"role": "user", "content": f"Assessment inputs:\n{json.dumps(context, indent=2)}"},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "decision",
                "schema": DECISION_SCHEMA,
                "strict": True,
            }
        },
    )
    return json.loads(resp.output_text)


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "name": "extract_document",
        "description": (
            "Extract structured summary, entities, and data quality issues "
            "from a medical document. Call this first with raw document text."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Raw text of the document"},
                "source_type": {
                    "type": "string",
                    "enum": ["text", "pdf"],
                    "description": "Pass 'text' when you already have the content",
                },
            },
            "required": ["source"],
        },
    },
    {
        "type": "function",
        "name": "check_completeness",
        "description": (
            "Check whether mandatory fields required for a claims decision are present. "
            "Pass entities and issues from extract_document."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "entities": {"type": "object"},
                "issues": {"type": "object"},
            },
            "required": ["entities", "issues"],
        },
    },
    {
        "type": "function",
        "name": "assess_medical_risk",
        "description": (
            "Assess medical underwriting risk from extracted diagnoses and medications. "
            "Returns risk_level: low | moderate | high | refer_to_underwriter."
        ),
        "parameters": {
            "type": "object",
            "properties": {"entities": {"type": "object"}},
            "required": ["entities"],
        },
    },
    {
        "type": "function",
        "name": "make_decision",
        "description": (
            "Produce final claims recommendation: APPROVE, REQUEST_DOCUMENTS, "
            "REFER_UNDERWRITER, or DECLINE_TRIAGE. Call this last."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "completeness": {"type": "object"},
                "medical_risk": {"type": "object"},
                "issues": {"type": "object"},
                "entities": {"type": "object"},
            },
            "required": ["completeness", "medical_risk", "issues", "entities"],
        },
    },
]


def run_claims_agent(
    document_text: str,
    client: OpenAI,
    model: str = DEFAULT_MODEL,
    verbose: bool = True,
) -> dict:
    """Run the end-to-end tool-calling claims triage loop.

    Flow:
    1) Send the document and tool catalog to the model.
    2) Execute any returned tool calls in Python.
    3) Return tool outputs to the model as function call outputs.
    4) Repeat until the model returns a final text summary.

    Args:
        document_text: Claim/medical document text to triage.
        client: Initialized OpenAI client.
        model: Model name used for orchestration and decision calls.
        verbose: Whether to print live progress logs.

    Returns:
        Session log containing tool calls, tool results, final decision, and
        model summary text.
    """

    def log(msg: str) -> None:
        """Print helper that respects the `verbose` flag."""
        if verbose:
            print(msg)

    log("\n" + "=" * 60)
    log("  CLAIMS ASSESSOR AGENT  -  Starting evaluation")
    log("=" * 60)

    messages = [
        {
            "role": "system",
            "content": (
                "You are an autonomous life insurance claims assessor agent.\n"
                "Use tools in this sequence when possible:\n"
                "1. extract_document\n"
                "2. check_completeness\n"
                "3. assess_medical_risk\n"
                "4. make_decision\n"
                "Do not guess final decisions before running completeness and risk checks."
            ),
        },
        {
            "role": "user",
            "content": (
                "Please assess the following life insurance claim document.\n\n"
                f"DOCUMENT:\n{document_text}"
            ),
        },
    ]

    session_log = {
        "tool_calls": [],
        "tool_results": {},
        "final_decision": None,
        "agent_summary": None,
    }

    max_iterations = 10
    iteration = 0
    # Required by the Responses API to continue an existing response chain.
    previous_response_id: Optional[str] = None

    def call_extract_document(**kwargs: dict) -> dict:
        """Adapter so tool dispatch can call extractor with shared client/model."""
        return extract_summary_and_entities(client=client, model=model, **kwargs)

    def call_make_decision(**kwargs: dict) -> dict:
        """Adapter so tool dispatch can call decision with shared client/model."""
        return make_decision(client=client, model=model, **kwargs)

    tool_dispatch = {
        "extract_document": call_extract_document,
        "check_completeness": check_completeness,
        "assess_medical_risk": assess_medical_risk,
        "make_decision": call_make_decision,
    }

    while iteration < max_iterations:
        iteration += 1
        log(f"\n[Agent loop - iteration {iteration}]")

        if previous_response_id is None:
            response = client.responses.create(model=model, input=messages, tools=TOOL_DEFINITIONS)
        else:
            response = client.responses.create(
                model=model,
                previous_response_id=previous_response_id,
                input=messages,
                tools=TOOL_DEFINITIONS,
            )
        previous_response_id = response.id

        output = response.output
        text_blocks = [item for item in output if item.type == "message"]
        tool_call_blocks = [item for item in output if item.type == "function_call"]

        if not tool_call_blocks:
            if text_blocks:
                # Flatten text segments from the model's final message payload.
                final_text = ""
                for block in text_blocks:
                    for content_item in block.content:
                        if hasattr(content_item, "text"):
                            final_text += content_item.text
                session_log["agent_summary"] = final_text
                log(f"\n[Agent final summary]\n{final_text}")
            break

        tool_outputs = []
        for tool_call in tool_call_blocks:
            tool_name = tool_call.name
            tool_args = json.loads(tool_call.arguments)
            call_id = tool_call.call_id

            log(f"  -> Tool call: {tool_name}({list(tool_args.keys())})")
            session_log["tool_calls"].append({"tool": tool_name, "args_keys": list(tool_args.keys())})

            if tool_name not in tool_dispatch:
                tool_result = {"error": f"Unknown tool: {tool_name}"}
            else:
                try:
                    tool_result = tool_dispatch[tool_name](**tool_args)
                except Exception as exc:
                    tool_result = {"error": str(exc)}

            session_log["tool_results"][tool_name] = tool_result

            if tool_name == "make_decision":
                session_log["final_decision"] = tool_result
                log(
                    f"\n  * DECISION: {tool_result.get('decision')} "
                    f"[confidence: {tool_result.get('confidence')}]"
                )
                log(f"  Rationale: {tool_result.get('rationale')}")

            tool_outputs.append(
                {
                    # Responses API format for returning tool results.
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps(tool_result),
                }
            )

        messages = tool_outputs

    log("\n" + "=" * 60)
    log("  AGENT SESSION COMPLETE")
    log("=" * 60)

    return session_log
