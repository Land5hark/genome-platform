import io
import sys
import tempfile
import zipfile
from pathlib import Path

from flask import Flask, jsonify, request, send_file

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024  # 25MB

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "Genetic Health" / "scripts"
DATA_DIR = REPO_ROOT / "Genetic Health" / "data"
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


def _dataset_status():
    required = {name: (DATA_DIR / name).exists() for name in REQUIRED_DATASETS}
    optional = {name: (DATA_DIR / name).exists() for name in OPTIONAL_DATASETS}
    ready = all(required.values())
    return {'ready': ready, 'required': required, 'optional': optional}


@app.post('/api/analyze')
def analyze():
    uploaded = request.files.get('genome_file')
    if not uploaded or uploaded.filename == '':
        return jsonify({'error': 'Missing genome_file upload'}), 400

    ext = Path(uploaded.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({'error': f'Unsupported file type: {ext}. Use .txt or .csv'}), 400

    subject_name = request.form.get('subject_name') or None

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        genome_path = tmp_path / f'genome_upload{ext}'
        reports_dir = tmp_path / 'reports'
        uploaded.save(genome_path)

        run_full_analysis(genome_path=genome_path, subject_name=subject_name, output_dir=reports_dir)

        output_names = [
            'EXHAUSTIVE_GENETIC_REPORT.md',
            'EXHAUSTIVE_DISEASE_RISK_REPORT.md',
            'ACTIONABLE_HEALTH_PROTOCOL_V3.md',
            'comprehensive_results.json',
        ]

        report_files = [reports_dir / name for name in output_names if (reports_dir / name).exists()]
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
    return jsonify({'status': 'ok', 'datasets': _dataset_status()})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
