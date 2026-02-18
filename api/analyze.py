import io
import json
import os
import shutil
import sys
import tempfile
import time
import uuid
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import stripe
from flask import Flask, jsonify, request, send_file, send_from_directory

app = Flask(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "Genetic Health" / "scripts"
SESSIONS_DIR = REPO_ROOT / ".sessions"
SESSIONS_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(SCRIPTS_DIR))

from run_full_analysis import REPORTS_DIR, run_full_analysis  # noqa: E402
from generate_summary_report import generate_summary_report  # noqa: E402

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")

REPORT_NAMES = [
    "EXHAUSTIVE_GENETIC_REPORT.md",
    "EXHAUSTIVE_DISEASE_RISK_REPORT.md",
    "ACTIONABLE_HEALTH_PROTOCOL_V3.md",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cleanup_old_sessions(max_age_hours: int = 24) -> None:
    """Delete session folders older than max_age_hours."""
    cutoff = time.time() - max_age_hours * 3600
    for folder in SESSIONS_DIR.iterdir():
        if folder.is_dir() and folder.stat().st_mtime < cutoff:
            shutil.rmtree(folder, ignore_errors=True)


def _build_teasers(results: dict) -> list[dict]:
    """
    Select 3-5 intriguing insight cards from analysis results.
    Each card reveals just enough to create curiosity without giving away
    the actionable detail — which lives in the full report.
    """
    teasers = []
    findings = results.get("findings", [])
    pharmgkb = results.get("pharmgkb_findings", [])

    # Sort by magnitude descending
    sorted_findings = sorted(
        findings, key=lambda x: x.get("magnitude", 0), reverse=True
    )

    # Category-to-plain-English hook templates
    HOOKS = {
        "Methylation": (
            "🧬",
            "Your {gene} Gene — A Hidden Driver of Energy & Mood",
            "A variant in your methylation pathway could quietly be affecting your "
            "energy levels, mental clarity, and cardiovascular health in ways most "
            "routine blood tests won't catch.",
            "What's the right form of folate for your specific variant?",
        ),
        "Drug Metabolism": (
            "💊",
            "Your {gene} Gene — How You Process Medications",
            "Your DNA shows a variant that changes how your liver metabolizes "
            "certain common medications — meaning standard doses may work "
            "differently for you than for most people.",
            "Which specific drug categories are affected, and by how much?",
        ),
        "Cardiovascular": (
            "❤️",
            "Your {gene} Gene — Heart & Circulation Signals",
            "A variant in a gene tied to blood pressure regulation and "
            "cardiovascular risk was detected in your genome. The implications "
            "depend on your full genetic context.",
            "What does your complete cardiovascular genetic profile look like?",
        ),
        "Neurotransmitters": (
            "🧠",
            "Your {gene} Gene — Stress Response & Mental Clarity",
            "A variant in your dopamine/stress pathway was found. This gene "
            "influences how your brain handles stress, focus, and emotional "
            "regulation — and it responds well to specific lifestyle changes.",
            "What targeted strategies work best for your specific variant?",
        ),
        "Nutrition": (
            "🥦",
            "Your {gene} Gene — Personalized Nutrition Signals",
            "Your DNA includes a variant affecting how efficiently you convert "
            "or absorb a key nutrient. Generic dietary advice may not be "
            "optimal for your unique biology.",
            "Which specific nutrients and foods matter most for your genes?",
        ),
        "Fitness": (
            "🏃",
            "Your {gene} Gene — Athletic & Recovery Profile",
            "A gene that influences muscle fiber composition and recovery speed "
            "shows a variant in your genome — with real implications for how "
            "your body responds to different types of exercise.",
            "What training approach is best matched to your genetics?",
        ),
        "Detoxification": (
            "🔬",
            "Your {gene} Gene — Detox Pathway Variant",
            "Your genome shows a variant in a detoxification enzyme that "
            "affects how your body processes environmental compounds and "
            "certain medications. This is worth knowing.",
            "What environmental or dietary factors matter most for your genes?",
        ),
    }

    DEFAULT_HOOK = (
        "🔬",
        "Your {gene} Gene — A Notable Variant",
        "A significant variant was detected in a gene linked to {category}. "
        "The full impact of this finding depends on your complete genetic context.",
        "What does your complete profile reveal about this area of your health?",
    )

    seen_categories = set()

    # Add top lifestyle/health findings (up to 3, prefer high magnitude, one per category)
    for f in sorted_findings:
        if len(teasers) >= 3:
            break
        mag = f.get("magnitude", 0)
        if mag < 1:
            continue
        category = f.get("category", "")
        if category in seen_categories:
            continue
        seen_categories.add(category)

        template = HOOKS.get(category, DEFAULT_HOOK)
        teasers.append({
            "icon": template[0],
            "title": template[1].format(gene=f["gene"]),
            "body": template[2],
            "hook": template[3].format(category=category.lower()),
        })

    # Add 1 pharmgkb teaser if available (pick Level 1 first)
    level1 = [p for p in pharmgkb if p.get("level", "").startswith("1")]
    pharma_pick = (level1 or pharmgkb or [None])[0]
    if pharma_pick and len(teasers) < 5:
        drugs_preview = pharma_pick.get("drugs", "common medications").split(",")[0].strip()
        teasers.append({
            "icon": "⚕️",
            "title": f"Your {pharma_pick['gene']} Gene — Medication Interaction",
            "body": (
                f"Clinical-grade evidence (Level {pharma_pick.get('level','1')}) shows "
                f"your {pharma_pick['gene']} variant affects how your body responds to "
                f"{drugs_preview} and related drugs. This is the kind of finding "
                f"pharmacists rarely check — but it matters."
            ),
            "hook": "What's the full list of affected medications and what should you tell your doctor?",
        })

    # Add disease risk teaser if any pathogenic/risk variants were found
    disease_stats = results.get("disease_stats", {})
    pathogenic = disease_stats.get("pathogenic_matched", 0)
    total_matched = disease_stats.get("matched", 0)
    if total_matched > 0 and len(teasers) < 5:
        if pathogenic > 0:
            body = (
                f"Your genome matched {total_matched} variants in the clinical disease "
                f"database — including {pathogenic} classified as pathogenic or "
                f"likely-pathogenic. Some may affect you directly; others may be "
                f"relevant for your family."
            )
            hook = "Which specific conditions are flagged, and what do they mean for you?"
        else:
            body = (
                f"Your genome matched {total_matched} variants in the clinical disease "
                f"risk database. Most are risk factors rather than certainties — but "
                f"knowing which ones you carry gives you a head start."
            )
            hook = "Which conditions show elevated risk, and what can you do about it?"
        teasers.append({
            "icon": "🏥",
            "title": "Disease Risk Screen — Variants Detected",
            "body": body,
            "hook": hook,
        })

    return teasers[:5]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get('/')
def index():
    return send_from_directory(REPO_ROOT, 'index.html')


@app.post('/api/analyze')
def analyze():
    _cleanup_old_sessions()

    uploaded = request.files.get('genome_file')
    if not uploaded or uploaded.filename == '':
        return jsonify({'error': 'Missing genome_file upload'}), 400

    subject_name = request.form.get('subject_name') or None
    from_ref = request.form.get('from_ref') or None
    analysis_id = str(uuid.uuid4())
    session_dir = SESSIONS_DIR / analysis_id
    session_dir.mkdir(parents=True, exist_ok=True)

    # Record which referral code brought this visitor (if any)
    if from_ref:
        (session_dir / "from_ref.txt").write_text(from_ref, encoding='utf-8')

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        ext = Path(uploaded.filename).suffix or '.txt'
        genome_path = tmp_path / f'genome_upload{ext}'
        uploaded.save(genome_path)

        run_full_analysis(genome_path=genome_path, subject_name=subject_name)

    # Copy reports and JSON into persistent session folder
    results_json_path = REPORTS_DIR / "comprehensive_results.json"
    if not results_json_path.exists():
        return jsonify({'error': 'Analysis produced no results'}), 500

    shutil.copy(results_json_path, session_dir / "comprehensive_results.json")
    for name in REPORT_NAMES:
        src = REPORTS_DIR / name
        if src.exists():
            shutil.copy(src, session_dir / name)

    # Store subject name alongside session data
    if subject_name:
        (session_dir / "subject_name.txt").write_text(subject_name, encoding='utf-8')

    # Build teaser response
    results = json.loads(results_json_path.read_text(encoding='utf-8'))
    teasers = _build_teasers(results)
    summary = results.get("summary", {})
    disease_stats = results.get("disease_stats", {})

    return jsonify({
        "analysis_id": analysis_id,
        "teaser": teasers,
        "stats": {
            "snps_analyzed": summary.get("total_snps", 0),
            "high_impact": summary.get("high_impact", 0),
            "drug_interactions": len(results.get("pharmgkb_findings", [])),
            "disease_variants": disease_stats.get("matched", 0),
        },
    })


ADD_ON_CATALOG = {
    # key: (display_name, unit_amount_cents, is_recurring)
    "pretty_print": ("Print-Ready Formatted Reports", 1900, False),
    "partner":      ("Partner / Family Member Report", 3900, False),
    "annual":       ("Annual DNA Updates", 2900, True),
    "deep_dive":    ("Raw Data Deep Dive", 4900, False),
}


@app.post('/api/checkout')
def checkout():
    data = request.get_json(silent=True) or {}
    analysis_id = data.get("analysis_id", "")
    subject_name = data.get("subject_name") or "report"
    add_ons: list[str] = data.get("add_ons") or []

    session_dir = SESSIONS_DIR / analysis_id
    if not analysis_id or not session_dir.exists():
        return jsonify({'error': 'Invalid or expired analysis session'}), 400

    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not stripe.api_key:
        return jsonify({'error': 'Payment not configured'}), 503

    # Save chosen add-ons into the session so /api/complete knows what to build
    (session_dir / "add_ons.json").write_text(json.dumps(add_ons), encoding='utf-8')

    # Pull the referrer code that brought this buyer (stored during /api/analyze)
    from_ref_file = session_dir / "from_ref.txt"
    from_ref = from_ref_file.read_text(encoding='utf-8').strip() if from_ref_file.exists() else None

    has_subscription = "annual" in add_ons
    mode = "subscription" if has_subscription else "payment"

    line_items = [{
        "price_data": {
            "currency": "usd",
            "unit_amount": 7900,
            "product_data": {
                "name": "Full Genome Analysis Report",
                "description": (
                    "4 personalized reports: Genetic Health, Disease Risk, "
                    "Actionable Health Protocol, and your plain-English Master Summary"
                ),
            },
        },
        "quantity": 1,
    }]

    for key in add_ons:
        if key not in ADD_ON_CATALOG:
            continue
        name, amount, recurring = ADD_ON_CATALOG[key]
        price_data: dict = {
            "currency": "usd",
            "unit_amount": amount,
            "product_data": {"name": name},
        }
        if recurring:
            price_data["recurring"] = {"interval": "year"}
        line_items.append({"price_data": price_data, "quantity": 1})

    add_ons_param = ",".join(add_ons) if add_ons else ""
    metadata = {"analysis_id": analysis_id, "add_ons": add_ons_param}
    if from_ref:
        metadata["from_ref"] = from_ref

    checkout_session = stripe.checkout.Session.create(
        mode=mode,
        line_items=line_items,
        success_url=(
            f"{BASE_URL}/success"
            f"?session_id={{CHECKOUT_SESSION_ID}}"
            f"&analysis_id={analysis_id}"
            f"&subject_name={subject_name}"
            f"&add_ons={add_ons_param}"
        ),
        cancel_url=f"{BASE_URL}/",
        metadata=metadata,
    )

    return jsonify({"checkout_url": checkout_session.url})


@app.get('/success')
def success_page():
    return send_from_directory(REPO_ROOT, 'thank-you.html')


def _make_pretty_html(title: str, markdown_content: str) -> str:
    """Wrap a markdown string in a self-contained styled HTML file that renders
    beautifully on screen and prints cleanly. Uses marked.js via CDN."""
    safe_md = json.dumps(markdown_content)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
  :root {{
    --bg:#0f0f10; --surface:#18181b; --border:#27272a;
    --text:#e4e4e7; --muted:#a1a1aa; --accent:#7c3aed;
  }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--text); font-family:'Segoe UI',system-ui,sans-serif;
         font-size:15px; line-height:1.7; padding:40px 20px; }}
  #report {{ max-width:780px; margin:0 auto; }}
  h1 {{ font-size:2rem; color:#fff; border-bottom:2px solid var(--accent);
        padding-bottom:16px; margin-bottom:24px; }}
  h2 {{ font-size:1.4rem; color:#c4b5fd; margin:36px 0 12px; }}
  h3 {{ font-size:1.1rem; color:#a78bfa; margin:24px 0 8px; }}
  p  {{ margin-bottom:14px; color:var(--text); }}
  ul, ol {{ margin:0 0 14px 24px; }}
  li {{ margin-bottom:6px; }}
  hr {{ border:none; border-top:1px solid var(--border); margin:32px 0; }}
  strong {{ color:#fff; }}
  em {{ color:var(--muted); }}
  blockquote {{ border-left:3px solid var(--accent); padding:12px 16px;
                background:var(--surface); border-radius:0 8px 8px 0; margin:16px 0; }}
  code {{ background:var(--surface); padding:2px 6px; border-radius:4px;
          font-family:monospace; font-size:0.88em; }}
  table {{ width:100%; border-collapse:collapse; margin:16px 0; }}
  th {{ background:var(--surface); color:#c4b5fd; padding:10px 12px;
        text-align:left; border-bottom:2px solid var(--border); }}
  td {{ padding:9px 12px; border-bottom:1px solid var(--border); }}
  .report-header {{ text-align:center; padding:32px; background:linear-gradient(135deg,#3b0764,#1e1b4b);
                    border-radius:12px; margin-bottom:40px; }}
  .report-header h1 {{ border:none; margin:0; }}
  .report-footer {{ margin-top:48px; padding-top:24px; border-top:1px solid var(--border);
                    color:var(--muted); font-size:0.82rem; text-align:center; }}
  @media print {{
    body {{ background:#fff; color:#111; font-size:12pt; }}
    h1 {{ color:#111; border-color:#6d28d9; }}
    h2 {{ color:#4c1d95; }} h3 {{ color:#5b21b6; }}
    .report-header {{ background:#f3e8ff; }}
    blockquote {{ background:#f5f3ff; border-color:#7c3aed; }}
    th {{ background:#f5f3ff; color:#4c1d95; }}
  }}
</style>
</head>
<body>
<div id="report">
  <div class="report-header">
    <h1>{title}</h1>
    <p style="color:#c4b5fd;margin-top:8px;">Personal Genome Analysis Report</p>
  </div>
  <div id="content"></div>
  <div class="report-footer">
    This report is for educational purposes only and does not constitute medical advice.
    Please consult a qualified healthcare provider before making any health decisions.
  </div>
</div>
<script>
  document.getElementById('content').innerHTML = marked.parse({safe_md});
</script>
</body>
</html>"""


@app.get('/api/complete')
def complete():
    session_id   = request.args.get("session_id", "")
    analysis_id  = request.args.get("analysis_id", "")
    subject_name = request.args.get("subject_name") or None

    session_dir = SESSIONS_DIR / analysis_id
    if not analysis_id or not session_dir.exists():
        return jsonify({'error': 'Invalid or expired analysis session'}), 400

    # Verify payment with Stripe
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if stripe.api_key:
        try:
            stripe_session = stripe.checkout.Session.retrieve(session_id)
            if stripe_session.payment_status != "paid":
                return jsonify({'error': 'Payment not completed'}), 402
        except stripe.StripeError as e:
            return jsonify({'error': f'Payment verification failed: {e}'}), 402

    # Load add-ons chosen at checkout
    add_ons_file = session_dir / "add_ons.json"
    add_ons: list[str] = json.loads(add_ons_file.read_text(encoding='utf-8')) if add_ons_file.exists() else []

    # Record referral conversion (append to referrals.json in repo root)
    from_ref_file = session_dir / "from_ref.txt"
    if from_ref_file.exists():
        referrals_path = REPO_ROOT / "referrals.json"
        try:
            referrals = json.loads(referrals_path.read_text(encoding='utf-8')) if referrals_path.exists() else []
        except Exception:
            referrals = []
        referrals.append({
            "from_ref": from_ref_file.read_text(encoding='utf-8').strip(),
            "analysis_id": analysis_id,
            "stripe_session": session_id,
            "timestamp": datetime.utcnow().isoformat(),
        })
        referrals_path.write_text(json.dumps(referrals, indent=2), encoding='utf-8')

    # Load subject name from session if not provided
    name_file = session_dir / "subject_name.txt"
    if not subject_name and name_file.exists():
        subject_name = name_file.read_text(encoding='utf-8').strip()

    # Generate the 4th master summary report
    results_path = session_dir / "comprehensive_results.json"
    master_report_path = session_dir / "MASTER_SUMMARY_REPORT.md"

    if not master_report_path.exists():
        results = json.loads(results_path.read_text(encoding='utf-8'))
        try:
            summary_md = generate_summary_report(results, subject_name=subject_name)
        except Exception as e:
            return jsonify({'error': f'Report generation failed: {e}'}), 500
        master_report_path.write_text(summary_md, encoding='utf-8')

    # Build ZIP of all 4 reports (+ pretty HTML if purchased)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        all_reports = list(REPORT_NAMES) + ["MASTER_SUMMARY_REPORT.md"]
        for name in all_reports:
            p = session_dir / name
            if p.exists():
                zf.write(p, arcname=f"reports/{name}")

        if "pretty_print" in add_ons:
            for name in all_reports:
                p = session_dir / name
                if p.exists():
                    md = p.read_text(encoding='utf-8')
                    display_name = name.replace("_", " ").replace(".md", "")
                    html = _make_pretty_html(display_name, md)
                    zf.writestr(f"pretty/{name.replace('.md', '.html')}", html.encode('utf-8'))

    zip_buffer.seek(0)
    safe_name = (subject_name or "report").replace(" ", "_")
    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f"genome-analysis-{safe_name}.zip",
    )


@app.get('/api/health')
def health():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
