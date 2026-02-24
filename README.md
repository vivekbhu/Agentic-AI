# Claims Triage Agent

Refactored multi-file version of the life insurance claims assessor agent.

## Project structure

```text
claims-triage-agent/
  README.md
  requirements.txt
  .env.example
  src/
    ingest.py
    schemas.py
    extractor.py
    rules.py
    agent.py
    run.py
  samples/
    sample_output.json
```

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and set your API key:

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini
```

## Run

From the `claims-triage-agent` folder:

```bash
python -m src.run
```

With a PDF:

```bash
python -m src.run "path/to/medical_report.pdf"
```

Optional flags:

```bash
python -m src.run --output out.json --quiet
```

