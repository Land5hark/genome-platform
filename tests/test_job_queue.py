import tempfile
import unittest
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
API_DIR = REPO_ROOT / 'api'
SCRIPTS_DIR = REPO_ROOT / 'Genetic Health' / 'scripts'
sys.path.insert(0, str(API_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))

import job_queue  # noqa: E402
from run_full_analysis import run_full_analysis  # noqa: E402


class JobQueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        job_queue.RUNTIME_DIR = root / 'runtime'
        job_queue.UPLOADS_DIR = job_queue.RUNTIME_DIR / 'uploads'
        job_queue.REPORTS_DIR = job_queue.RUNTIME_DIR / 'reports'
        job_queue.ARTIFACTS_DIR = job_queue.RUNTIME_DIR / 'artifacts'
        job_queue.DB_PATH = job_queue.RUNTIME_DIR / 'jobs.sqlite3'
        job_queue.artifact_store = job_queue.LocalArtifactStore()
        job_queue.init_db()

    def tearDown(self):
        self.tmp.cleanup()

    def test_enqueue_process_and_zip(self):
        genome_bytes = (REPO_ROOT / 'AncestryDNA.txt').read_bytes()
        job_id = job_queue.enqueue_job('AncestryDNA.txt', genome_bytes, 'Queue Test')

        queued = job_queue.get_job(job_id)
        self.assertEqual('queued', queued['status'])

        processed = job_queue.process_next_job(run_full_analysis)
        self.assertIsNotNone(processed)
        self.assertEqual(job_id, processed['id'])

        completed = job_queue.get_job(job_id)
        self.assertEqual('completed', completed['status'])
        self.assertTrue(Path(completed['storage_key']).exists())

    def test_failed_job_sets_status(self):
        genome_bytes = b'bad-data'
        job_id = job_queue.enqueue_job('bad.txt', genome_bytes, 'Fail Test')

        def boom(*_args, **_kwargs):
            raise RuntimeError('simulated failure')

        processed = job_queue.process_next_job(boom)
        self.assertEqual(job_id, processed['id'])

        failed = job_queue.get_job(job_id)
        self.assertEqual('failed', failed['status'])
        self.assertIn('simulated failure', failed['error'])

    def test_cleanup_expired_jobs(self):
        genome_bytes = (REPO_ROOT / 'AncestryDNA.txt').read_bytes()
        job_id = job_queue.enqueue_job('AncestryDNA.txt', genome_bytes, 'Cleanup')
        # Force old timestamp then cleanup aggressively
        job_queue.update_job(job_id, created_at='2000-01-01T00:00:00+00:00')

        result = job_queue.cleanup_expired_jobs(upload_ttl_hours=0, artifact_ttl_days=0, job_ttl_days=0)
        self.assertGreaterEqual(result['removed_jobs'], 1)


if __name__ == '__main__':
    unittest.main()
