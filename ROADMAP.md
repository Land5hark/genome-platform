# Genome Intelligence Platform — Rapid Execution Roadmap

## Goal (Hours, not days)
Ship a working MVP that lets a user upload raw DNA data, runs the existing analysis pipeline, and returns the generated reports through a deployable Vercel app.

## Phase 1 — Stabilize Core Analysis (Immediate)
- [x] Ensure parser supports both common raw DNA formats:
  - 23andMe-style: `rsid chrom pos genotype`
  - Ancestry-style: `rsid chrom pos allele1 allele2`
- [x] Keep existing report generation pipeline intact (`run_full_analysis.py`).

**Acceptance criteria:** Running pipeline with the provided `AncestryDNA.txt` no longer depends on single-allele parsing behavior.

## Phase 2 — Build MVP Web Interface (Immediate)
- [x] Add a single-page web UI:
  - Upload `.txt`/`.csv` DNA file
  - Optional subject name
  - Trigger analysis
  - Download zipped reports
- [x] Add API endpoint that executes analysis and returns output ZIP.

**Acceptance criteria:** User can upload a genome file and receive report artifacts in one flow.

## Phase 3 — Make Deployable (Immediate)
- [x] Add Vercel configuration for static + Python serverless routing.
- [x] Add Python dependencies file.
- [x] Document local run and Vercel deploy commands.

**Acceptance criteria:** `vercel` deployment can route `/` to UI and `/api/analyze` to backend.

## Phase 4 — Validate & Hand Off
- [x] Run static checks (`py_compile`) for Python changes.
- [x] Run smoke test via Flask test client against `/api/analyze`.
- [x] Commit and produce PR notes.

## Next (Post-MVP hardening)
- Add queue/async job execution for long-running analyses.
- Add strict legal/compliance content in UI + explicit consent gates.
- Add authentication and private report storage with expiration.
- Add report quality tests against known fixtures.
