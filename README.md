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

## Streamlit Demo UI

Run a public demo UI locally:

```bash
streamlit run streamlit_app.py
```

What it does:
- lets users upload a PDF medical report
- runs the backend agent from `src/agent.py`
- shows decision, confidence, rationale, and full JSON output

## Deploy Public Demo (Streamlit Community Cloud)

1. Push this repo to GitHub.
2. In Streamlit Community Cloud, create a new app from this repo.
3. Set entrypoint to `streamlit_app.py`.
4. In app secrets/settings, set:
   - `OPENAI_API_KEY`
   - optional: `OPENAI_MODEL` (defaults to `gpt-4.1-mini`)
5. Deploy and share the generated public URL.

Important: use synthetic/sample reports only. Do not upload real PHI.

