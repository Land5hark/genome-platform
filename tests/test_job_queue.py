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
        job_queue.DB_PATH = job_queue.RUNTIME_DIR / 'jobs.sqlite3'
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
        self.assertTrue(Path(completed['zip_path']).exists())


if __name__ == '__main__':
    unittest.main()
