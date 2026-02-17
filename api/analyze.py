import mimetypes
import sys
import threading
from pathlib import Path

from flask import Flask, jsonify, request, send_file

from job_queue import (
    init_db,
    enqueue_job,
    get_job,
    list_recent_jobs,
    worker_loop,
    process_next_job,
)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024  # 25MB

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / 'Genetic Health' / 'scripts'
DATA_DIR = REPO_ROOT / 'Genetic Health' / 'data'
sys.path.insert(0, str(SCRIPTS_DIR))

from run_full_analysis import run_full_analysis  # noqa: E402

ALLOWED_EXTENSIONS = {'.txt', '.csv'}
REQUIRED_DATASETS = [
    'clinical_annotations.tsv',
    'clinical_ann_alleles.tsv',
]
OPTIONAL_DATASETS = [
    'clinvar_alleles.tsv',
]

_worker_started = False


def _dataset_status():
    required = {name: (DATA_DIR / name).exists() for name in REQUIRED_DATASETS}
    optional = {name: (DATA_DIR / name).exists() for name in OPTIONAL_DATASETS}
    ready = all(required.values())
    return {'ready': ready, 'required': required, 'optional': optional}


def _serialize_job(job: dict):
    response = {
        'id': job['id'],
        'status': job['status'],
        'subject_name': job.get('subject_name'),
        'upload_name': job.get('upload_name'),
        'error': job.get('error'),
        'created_at': job.get('created_at'),
        'updated_at': job.get('updated_at'),
        'started_at': job.get('started_at'),
        'completed_at': job.get('completed_at'),
    }
    if job.get('status') == 'completed':
        response['download_url'] = f"/api/jobs/{job['id']}/download"
    return response


def _start_worker_once():
    global _worker_started
    if _worker_started:
        return
    init_db()
    thread = threading.Thread(target=worker_loop, args=(run_full_analysis,), daemon=True)
    thread.start()
    _worker_started = True


@app.before_request
def _ensure_worker():
    if app.config.get('DISABLE_BACKGROUND_WORKER'):
        return
    _start_worker_once()


@app.post('/api/jobs')
def create_job():
    uploaded = request.files.get('genome_file')
    if not uploaded or uploaded.filename == '':
        return jsonify({'error': 'Missing genome_file upload'}), 400

    ext = Path(uploaded.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({'error': f'Unsupported file type: {ext}. Use .txt or .csv'}), 400

    subject_name = request.form.get('subject_name') or None
    job_id = enqueue_job(uploaded.filename, uploaded.read(), subject_name)
    job = get_job(job_id)
    return jsonify({'job': _serialize_job(job)}), 202


@app.get('/api/jobs/<job_id>')
def get_job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify({'job': _serialize_job(job)})


@app.get('/api/jobs/<job_id>/download')
def download_job(job_id: str):
    job = get_job(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    if job['status'] != 'completed' or not job.get('zip_path'):
        return jsonify({'error': 'Job not completed yet'}), 409

    zip_path = Path(job['zip_path'])
    if not zip_path.exists():
        return jsonify({'error': 'Report archive not found'}), 410

    mimetype, _ = mimetypes.guess_type(str(zip_path))
    return send_file(
        zip_path,
        mimetype=mimetype or 'application/zip',
        as_attachment=True,
        download_name=f"genome-analysis-{job_id}.zip",
    )


# Backward-compatible endpoint; now async.
@app.post('/api/analyze')
def analyze_compat():
    return create_job()


@app.get('/api/health')
def health():
    queued = [j for j in list_recent_jobs(50) if j['status'] == 'queued']
    processing = [j for j in list_recent_jobs(50) if j['status'] == 'processing']
    return jsonify(
        {
            'status': 'ok',
            'datasets': _dataset_status(),
            'queue': {
                'queued_count': len(queued),
                'processing_count': len(processing),
                'worker_started': _worker_started,
            },
        }
    )


@app.post('/api/admin/process-once')
def admin_process_once():
    job = process_next_job(run_full_analysis)
    if not job:
        return jsonify({'processed': False})
    return jsonify({'processed': True, 'job': _serialize_job(job)})


if __name__ == '__main__':
    _start_worker_once()
    app.run(host='0.0.0.0', port=8000, debug=True)
