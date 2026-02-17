import os
import sqlite3
import tempfile
import threading
import time
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

RUNTIME_DIR = Path(tempfile.gettempdir()) / 'genome_platform_runtime'
UPLOADS_DIR = RUNTIME_DIR / 'uploads'
REPORTS_DIR = RUNTIME_DIR / 'reports'
ARTIFACTS_DIR = RUNTIME_DIR / 'artifacts'
DB_PATH = RUNTIME_DIR / 'jobs.sqlite3'

_LOCK = threading.Lock()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value)


def ensure_runtime_dirs() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def get_conn():
    ensure_runtime_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class ArtifactStore:
    def put_zip(self, job_id: str, zip_path: Path) -> str:  # pragma: no cover - interface
        raise NotImplementedError

    def get_zip_path(self, storage_key: str) -> Optional[Path]:  # pragma: no cover - interface
        raise NotImplementedError


class LocalArtifactStore(ArtifactStore):
    def put_zip(self, job_id: str, zip_path: Path) -> str:
        dest = ARTIFACTS_DIR / f'{job_id}.zip'
        dest.write_bytes(zip_path.read_bytes())
        return str(dest)

    def get_zip_path(self, storage_key: str) -> Optional[Path]:
        path = Path(storage_key)
        return path if path.exists() else None


artifact_store = LocalArtifactStore()


def init_db() -> None:
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
                storage_key TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                request_id TEXT
            )
            """
        )
        # Backward-compatible migration for pre-existing DBs
        existing_cols = {r['name'] for r in conn.execute("PRAGMA table_info(jobs)").fetchall()}
        if 'storage_key' not in existing_cols:
            conn.execute("ALTER TABLE jobs ADD COLUMN storage_key TEXT")
        if 'request_id' not in existing_cols:
            conn.execute("ALTER TABLE jobs ADD COLUMN request_id TEXT")
        conn.commit()


def enqueue_job(upload_name: str, upload_bytes: bytes, subject_name: str | None = None, request_id: str | None = None) -> str:
    job_id = str(uuid.uuid4())
    ext = Path(upload_name).suffix.lower() or '.txt'
    upload_path = UPLOADS_DIR / f'{job_id}{ext}'
    upload_path.write_bytes(upload_bytes)

    now = utc_now()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO jobs (id, status, subject_name, upload_name, upload_path, created_at, updated_at, request_id)
            VALUES (?, 'queued', ?, ?, ?, ?, ?, ?)
            """,
            (job_id, subject_name, upload_name, str(upload_path), now, now, request_id),
        )
        conn.commit()

    return job_id


def get_job(job_id: str):
    with get_conn() as conn:
        row = conn.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
    return dict(row) if row else None


def update_job(job_id: str, **fields) -> None:
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
            row = conn.execute("SELECT * FROM jobs WHERE status = 'queued' ORDER BY created_at ASC LIMIT 1").fetchone()
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


def build_zip(reports_dir: Path, zip_path: Path) -> None:
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
        storage_key = artifact_store.put_zip(job_id, zip_path)
        update_job(
            job_id,
            status='completed',
            reports_dir=str(reports_dir),
            storage_key=storage_key,
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


def cleanup_expired_jobs(upload_ttl_hours: int = 24, artifact_ttl_days: int = 7, job_ttl_days: int = 7) -> dict:
    now = datetime.now(timezone.utc)
    upload_cutoff = now - timedelta(hours=upload_ttl_hours)
    artifact_cutoff = now - timedelta(days=artifact_ttl_days)
    job_cutoff = now - timedelta(days=job_ttl_days)

    removed_uploads = 0
    removed_artifacts = 0
    removed_jobs = 0

    with get_conn() as conn:
        rows = conn.execute('SELECT * FROM jobs').fetchall()
        for row in rows:
            job = dict(row)
            created_at = parse_utc(job['created_at'])

            upload_path = Path(job['upload_path'])
            if created_at < upload_cutoff and upload_path.exists():
                upload_path.unlink(missing_ok=True)
                removed_uploads += 1

            storage_key = job.get('storage_key')
            if storage_key and created_at < artifact_cutoff:
                artifact = artifact_store.get_zip_path(storage_key)
                if artifact and artifact.exists():
                    artifact.unlink(missing_ok=True)
                    removed_artifacts += 1

            if created_at < job_cutoff:
                conn.execute('DELETE FROM jobs WHERE id = ?', (job['id'],))
                removed_jobs += 1

        conn.commit()

    return {
        'removed_uploads': removed_uploads,
        'removed_artifacts': removed_artifacts,
        'removed_jobs': removed_jobs,
    }
