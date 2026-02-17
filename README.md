# Genome Platform

A genome intelligence platform for health insights and genetic analysis.

## What works now

- Dark-mode landing page with built-in DNA upload/analyze flow (`index.html` + `api/analyze.py`)
- End-to-end analysis via existing Python pipeline in `Genetic Health/scripts/run_full_analysis.py`
- API writes report artifacts to an isolated temp directory per request (serverless-safe)
- ZIP download containing generated report files

## Data prerequisites

Required for core analysis:
- `Genetic Health/data/clinical_annotations.tsv`
- `Genetic Health/data/clinical_ann_alleles.tsv`

Optional for disease-risk section:
- `Genetic Health/data/clinvar_alleles.tsv`

You can verify readiness using:

```bash
curl http://localhost:8000/api/health
```

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
- `/` → landing page UI
- `/api/analyze` → analysis endpoint (multipart form: `genome_file`, optional `subject_name`)
- `/api/health` → dataset readiness / service health

## Notes for production

- Current API is synchronous; for high traffic or large workloads, move analysis to queued background jobs.
- Uploads are currently limited to 25MB via Flask `MAX_CONTENT_LENGTH`.

## Project docs

- `ROADMAP.md` — rapid execution plan and acceptance criteria
- `genome-intelligence-platform-research.md` — viability/market/legal analysis
- `genome-platform-marketing.md` — positioning and messaging
- `Genetic Health/CLAUDE.md` — analysis pipeline operations

---
*Built for the RedEyedJedi ecosystem*
