import io
import tempfile
import unittest
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
API_DIR = REPO_ROOT / 'api'
SCRIPTS_DIR = REPO_ROOT / 'Genetic Health' / 'scripts'
sys.path.insert(0, str(API_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))

try:
    import flask  # noqa: F401
    FLASK_AVAILABLE = True
except Exception:
    FLASK_AVAILABLE = False

if FLASK_AVAILABLE:
    import analyze  # noqa: E402
    import job_queue  # noqa: E402


@unittest.skipUnless(FLASK_AVAILABLE, 'Flask not available in this environment')
class AsyncApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)

        # Rebind runtime paths for isolation
        job_queue.RUNTIME_DIR = root / 'runtime'
        job_queue.UPLOADS_DIR = job_queue.RUNTIME_DIR / 'uploads'
        job_queue.REPORTS_DIR = job_queue.RUNTIME_DIR / 'reports'
        job_queue.DB_PATH = job_queue.RUNTIME_DIR / 'jobs.sqlite3'
        job_queue.init_db()

        analyze._worker_started = False
        analyze.app.config['DISABLE_BACKGROUND_WORKER'] = True
        self.client = analyze.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def test_create_job_and_status(self):
        payload = {
            'subject_name': 'API Test',
            'genome_file': (io.BytesIO((REPO_ROOT / 'AncestryDNA.txt').read_bytes()), 'AncestryDNA.txt'),
        }
        response = self.client.post('/api/jobs', data=payload, content_type='multipart/form-data')
        self.assertEqual(202, response.status_code)
        job_id = response.get_json()['job']['id']

        status_resp = self.client.get(f'/api/jobs/{job_id}')
        self.assertEqual(200, status_resp.status_code)
        self.assertIn(status_resp.get_json()['job']['status'], {'queued', 'processing', 'completed'})


if __name__ == '__main__':
    unittest.main()
