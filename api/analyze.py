import io
import sys
import tempfile
import zipfile
from pathlib import Path

from flask import Flask, jsonify, request, send_file

app = Flask(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "Genetic Health" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from run_full_analysis import REPORTS_DIR, run_full_analysis  # noqa: E402


@app.post('/api/analyze')
def analyze():
    uploaded = request.files.get('genome_file')
    if not uploaded or uploaded.filename == '':
        return jsonify({'error': 'Missing genome_file upload'}), 400

    subject_name = request.form.get('subject_name') or None

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        ext = Path(uploaded.filename).suffix or '.txt'
        genome_path = tmp_path / f'genome_upload{ext}'
        uploaded.save(genome_path)

        run_full_analysis(genome_path=genome_path, subject_name=subject_name)

        output_names = [
            "EXHAUSTIVE_GENETIC_REPORT.md",
            "EXHAUSTIVE_DISEASE_RISK_REPORT.md",
            "ACTIONABLE_HEALTH_PROTOCOL_V3.md",
            "comprehensive_results.json",
        ]

        # Collect existing reports (disease report may be absent if no ClinVar hit/data)
        report_files = [REPORTS_DIR / name for name in output_names if (REPORTS_DIR / name).exists()]
        if not report_files:
            return jsonify({'error': 'No reports were generated'}), 500

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in report_files:
                zf.write(file_path, arcname=file_path.name)

        zip_buffer.seek(0)
        filename = f"genome-analysis-{(subject_name or 'report').replace(' ', '_')}.zip"
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=filename,
        )


@app.get('/api/health')
def health():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
