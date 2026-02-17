# Genome Platform

A genome intelligence platform for health insights and genetic analysis.

## What works now

- Dark-mode landing page with built-in DNA upload/analyze flow (`index.html` + `api/analyze.py`)
- End-to-end analysis via existing Python pipeline in `Genetic Health/scripts/run_full_analysis.py`
- ZIP download containing generated report files

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python api/analyze.py
```

Then open `http://localhost:8000` and upload a raw DNA file (e.g., `AncestryDNA.txt`).

## Deploy to Vercel

```bash
npm i -g vercel
vercel
```

Routes:
- `/` → upload UI
- `/api/analyze` → analysis endpoint (multipart form: `genome_file`, optional `subject_name`)

## Project docs

- `ROADMAP.md` — rapid execution plan and acceptance criteria
- `genome-intelligence-platform-research.md` — viability/market/legal analysis
- `genome-platform-marketing.md` — positioning and messaging
- `Genetic Health/CLAUDE.md` — analysis pipeline operations

---
*Built for the RedEyedJedi ecosystem*
