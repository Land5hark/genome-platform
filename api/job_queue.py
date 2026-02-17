import json
import sqlite3
import tempfile
import threading
import time
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

RUNTIME_DIR = Path(tempfile.gettempdir()) / 'genome_platform_runtime'
UPLOADS_DIR = RUNTIME_DIR / 'uploads'
REPORTS_DIR = RUNTIME_DIR / 'reports'
DB_PATH = RUNTIME_DIR / 'jobs.sqlite3'

_LOCK = threading.Lock()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def ensure_runtime_dirs():
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def get_conn():
    ensure_runtime_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                subject_name TEXT,
                upload_name TEXT NOT NULL,
                upload_path TEXT NOT NULL,
                reports_dir TEXT,
                zip_path TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT
            )
            """
        )
        conn.commit()


def enqueue_job(upload_name: str, upload_bytes: bytes, subject_name: str | None = None):
    job_id = str(uuid.uuid4())
    ext = Path(upload_name).suffix.lower() or '.txt'
    upload_path = UPLOADS_DIR / f'{job_id}{ext}'
    upload_path.write_bytes(upload_bytes)

    now = utc_now()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO jobs (id, status, subject_name, upload_name, upload_path, created_at, updated_at)
            VALUES (?, 'queued', ?, ?, ?, ?, ?)
            """,
            (job_id, subject_name, upload_name, str(upload_path), now, now),
        )
        conn.commit()

    return job_id


def get_job(job_id: str):
    with get_conn() as conn:
        row = conn.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
    if not row:
        return None
    return dict(row)


def update_job(job_id: str, **fields):
    if not fields:
        return
    fields['updated_at'] = utc_now()
    keys = list(fields.keys())
    values = [fields[k] for k in keys]
    set_clause = ', '.join(f'{k} = ?' for k in keys)
    with get_conn() as conn:
        conn.execute(f'UPDATE jobs SET {set_clause} WHERE id = ?', (*values, job_id))
        conn.commit()


def list_recent_jobs(limit: int = 20):
    with get_conn() as conn:
        rows = conn.execute('SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?', (limit,)).fetchall()
    return [dict(r) for r in rows]


def claim_next_job():
    with _LOCK:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE status = 'queued' ORDER BY created_at ASC LIMIT 1"
            ).fetchone()
            if not row:
                return None
            job_id = row['id']
            now = utc_now()
            conn.execute(
                "UPDATE jobs SET status='processing', started_at=?, updated_at=? WHERE id=?",
                (now, now, job_id),
            )
            conn.commit()
            updated = conn.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
            return dict(updated)


def build_zip(reports_dir: Path, zip_path: Path):
    output_names = [
        'EXHAUSTIVE_GENETIC_REPORT.md',
        'EXHAUSTIVE_DISEASE_RISK_REPORT.md',
        'ACTIONABLE_HEALTH_PROTOCOL_V3.md',
        'comprehensive_results.json',
    ]
    report_files = [reports_dir / name for name in output_names if (reports_dir / name).exists()]
    if not report_files:
        raise RuntimeError('No reports were generated')

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for path in report_files:
            zf.write(path, arcname=path.name)


def process_next_job(run_full_analysis_func):
    job = claim_next_job()
    if not job:
        return None

    job_id = job['id']
    upload_path = Path(job['upload_path'])
    reports_dir = REPORTS_DIR / job_id
    reports_dir.mkdir(parents=True, exist_ok=True)
    zip_path = REPORTS_DIR / f'{job_id}.zip'

    try:
        run_full_analysis_func(
            genome_path=upload_path,
            subject_name=job.get('subject_name'),
            output_dir=reports_dir,
        )
        build_zip(reports_dir, zip_path)
        update_job(
            job_id,
            status='completed',
            reports_dir=str(reports_dir),
            zip_path=str(zip_path),
            completed_at=utc_now(),
            error=None,
        )
    except Exception as exc:
        update_job(job_id, status='failed', error=str(exc), completed_at=utc_now())

    return get_job(job_id)


def worker_loop(run_full_analysis_func, poll_interval_s: float = 1.5):
    while True:
        processed = process_next_job(run_full_analysis_func)
        if processed is None:
            time.sleep(poll_interval_s)
