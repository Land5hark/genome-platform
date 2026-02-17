# Genome Platform

A genome intelligence platform for health insights and genetic analysis.

## What works now

- Dark-mode landing page with built-in DNA upload/analyze flow (`index.html` + `api/analyze.py`)
- Async job API with SQLite-backed job table and background worker loop
- End-to-end analysis via existing Python pipeline in `Genetic Health/scripts/run_full_analysis.py`
- API writes report artifacts to isolated runtime directories and serves downloadable ZIP bundles

## Data prerequisites

Required for core analysis:
- `Genetic Health/data/clinical_annotations.tsv`
- `Genetic Health/data/clinical_ann_alleles.tsv`

Optional for disease-risk section:
- `Genetic Health/data/clinvar_alleles.tsv`

You can verify readiness and queue status using:

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

## API endpoints

- `POST /api/jobs` — enqueue analysis (multipart: `genome_file`, optional `subject_name`)
- `GET /api/jobs/<job_id>` — poll job status
- `GET /api/jobs/<job_id>/download` — download ZIP after completion
- `POST /api/analyze` — backward-compatible alias to `POST /api/jobs`
- `GET /api/health` — dataset + queue diagnostics

## Automated tests

```bash
python -m py_compile api/analyze.py api/job_queue.py 'Genetic Health/scripts/run_full_analysis.py'
python -m unittest discover -s tests -v
```

## Deploy to Vercel

```bash
npm i -g vercel
vercel
```

Routes:
- `/` → landing page UI
- `/api/*` → Python API

## Notes for production

- Current queue uses local SQLite + in-process worker thread; for multi-instance production, move to Redis/Postgres + external worker.
- Uploads are limited to 25MB via Flask `MAX_CONTENT_LENGTH`.

## Project docs

- `ROADMAP.md` — rapid execution plan and acceptance criteria
- `genome-intelligence-platform-research.md` — viability/market/legal analysis
- `genome-platform-marketing.md` — positioning and messaging
- `Genetic Health/CLAUDE.md` — analysis pipeline operations

---
*Built for the RedEyedJedi ecosystem*
