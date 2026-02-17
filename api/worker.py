import sys
from pathlib import Path

from job_queue import init_db, worker_loop

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / 'Genetic Health' / 'scripts'
sys.path.insert(0, str(SCRIPTS_DIR))

from run_full_analysis import run_full_analysis  # noqa: E402


def main():
    init_db()
    worker_loop(run_full_analysis)


if __name__ == '__main__':
    main()
