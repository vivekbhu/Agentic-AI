"""CLI entrypoint for running the claims triage agent.

This module handles:
1) command-line parsing
2) environment/model initialization
3) document loading (explicit input, local sample PDF, or demo text)
4) running the orchestrator and writing JSON output
"""

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from .agent import DEFAULT_MODEL, run_claims_agent
from .ingest import pdf_to_text


SAMPLE_PDF_NAME = "sample.pdf"

# Synthetic fallback document used when no PDF is supplied/found.
DEMO_DOC = """
MEDICAL REPORT (SYNTHETIC - for demonstration only)
Patient: Jane Doe
DOB: 1978-04-12
Report Date: 2024-11-02
Provider: Dr Amit Sharma, Cardiologist

History: Presented with chest pain and shortness of breath on 2024-10-29.
Assessment: Acute coronary syndrome ruled out. Diagnosis: Stable angina.
Investigations: ECG normal. Troponin negative.
Plan: Start Aspirin 100mg daily and Atorvastatin 40mg nightly. Follow-up in 2 weeks.
Procedure: Stress echocardiogram scheduled for 2024-11-10.
""".strip()


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for input selection, verbosity, and output path."""
    parser = argparse.ArgumentParser(description="Run the claims triage agent.")
    parser.add_argument("input", nargs="?", help="Optional PDF path.")
    parser.add_argument(
        "--output",
        default="claims_session_log.json",
        help="Output JSON path for full session log.",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose agent trace.")
    return parser.parse_args()


def load_default_document() -> str:
    """Load a default document when no input path is provided.

    Priority:
    1) `sample.pdf` in the same folder as this file
    2) first `*.pdf` found in the same folder
    3) built-in synthetic demo text
    """
    run_dir = Path(__file__).resolve().parent
    preferred_sample = run_dir / SAMPLE_PDF_NAME

    if preferred_sample.exists():
        print(f"No PDF provided - loading sample PDF: {preferred_sample}\n")
        text = pdf_to_text(str(preferred_sample))
        if not text.strip():
            raise RuntimeError(f"No text extracted from sample PDF: {preferred_sample}")
        return text

    pdf_candidates = sorted(run_dir.glob("*.pdf"))
    if pdf_candidates:
        sample_pdf = pdf_candidates[0]
        print(f"No PDF provided - loading PDF in run folder: {sample_pdf}\n")
        text = pdf_to_text(str(sample_pdf))
        if not text.strip():
            raise RuntimeError(f"No text extracted from sample PDF: {sample_pdf}")
        return text

    print("No PDF provided and no PDF found beside run.py - using built-in demo document.\n")
    return DEMO_DOC


def main() -> None:
    """CLI main: initialize client, load document, run agent, persist result."""
    args = parse_args()
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not found. Add it to .env.")

    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    client = OpenAI(api_key=api_key)

    if args.input:
        print(f"Loading PDF: {args.input}")
        document_text = pdf_to_text(args.input)
        if not document_text.strip():
            raise RuntimeError("No text extracted from PDF. The file may be scanned/image-based.")
    else:
        document_text = load_default_document()

    result = run_claims_agent(
        document_text=document_text,
        client=client,
        model=model,
        verbose=not args.quiet,
    )

    output_path = Path(args.output)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nFull session log saved to: {output_path}")


if __name__ == "__main__":
    main()
