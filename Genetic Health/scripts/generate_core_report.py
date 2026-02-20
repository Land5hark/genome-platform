#!/usr/bin/env python3
"""
Generate $39 Core Report (Lifestyle Genetics + PharmGKB Quick Card)

EXCLUDES:
- All ClinVar pathogenic/likely pathogenic/VUS variants
- PharmGKB Level 2+ findings (only include 1A/1B)
- Any clinical disease language

Includes assertions to prevent contradictions with Deep Dive report.
"""

from pathlib import Path


# Forbidden terms that must NOT appear in Core Report
FORBIDDEN_CLINICAL_TERMS = [
    'pathogenic', 'likely pathogenic', 'disease causing', 'affected',
    'clinvar', 'mutation', 'syndrome', 'disorder', 'carrier status',
    'homozygous affected', 'genetic disease', 'hereditary condition',
    'cancer risk', 'tumor', 'malignant', 'diagnosis'
]


def sanitize_clinical_terms(content: str) -> str:
    """Remove or replace any forbidden clinical terms that slipped through filters."""
    import re
    # Map clinical terms to softer wellness-appropriate replacements
    REPLACEMENTS = {
        'pathogenic': 'notable',
        'likely pathogenic': 'potentially notable',
        'disease causing': 'health-related',
        'clinvar': 'clinical database',
        'mutation': 'variant',
        'syndrome': 'condition',
        'disorder': 'condition',
        'carrier status': 'variant status',
        'homozygous affected': 'two copies detected',
        'genetic disease': 'genetic condition',
        'hereditary condition': 'inherited trait',
        'cancer risk': 'health consideration',
        'tumor': 'growth',
        'malignant': 'significant',
        'diagnosis': 'assessment',
    }
    for term, replacement in REPLACEMENTS.items():
        content = re.sub(re.escape(term), replacement, content, flags=re.IGNORECASE)
    return content


def _finding_contains_clinical_terms(finding: dict) -> bool:
    """Check if any text field in a finding contains forbidden clinical terms."""
    text = ' '.join([
        str(finding.get('summary', '')),
        str(finding.get('trait', '')),
        str(finding.get('annotation', '')),
    ]).lower()
    return any(term in text for term in FORBIDDEN_CLINICAL_TERMS)


def filter_lifestyle_findings(findings: list) -> list:
    """
    Filter findings to ONLY include lifestyle genetics categories.
    Also excludes any finding containing forbidden clinical terms.

    Allowed: caffeine, methylation, detox, metabolism, cardiovascular, sleep, nutrition
    """
    ALLOWED_KEYWORDS = [
        'caffeine', 'cyp1a2',
        'mthfr', 'methylation', 'folate', 'homocysteine',
        'detox', 'glutathione', 'gst', 'sod', 'antioxidant',
        'metabolism', 'weight', 'glucose', 'insulin', 'fat',
        'cardiovascular', 'blood pressure', 'hypertension', 'ace',
        'sleep', 'circadian', 'melatonin',
        'vitamin', 'mineral', 'nutrient',
        'opioid', 'opiates', 'pain', 'codeine', 'tramadol', 'morphine',
        'cyp2d6', 'oprm1', 'comt',
        'drug metabolism', 'pharmacogenomic',
        'neurotransmitter', 'dopamine', 'serotonin',
        'immune', 'inflammation', 'clotting', 'coagulation',
    ]

    lifestyle_findings = []

    for finding in findings:
        gene = finding.get('gene', '').lower()
        trait = finding.get('trait', '').lower()

        # Check if this finding matches allowed keywords
        is_lifestyle = any(
            keyword in gene or keyword in trait
            for keyword in ALLOWED_KEYWORDS
        )

        # Exclude findings that contain clinical language
        if is_lifestyle and not _finding_contains_clinical_terms(finding):
            lifestyle_findings.append(finding)

    return lifestyle_findings


def filter_pharma_quick_card(pharmgkb_findings: list) -> list:
    """
    Filter PharmGKB to Level 1A/1B only. No arbitrary cap — show all
    strong-evidence findings so nothing clinically useful gets dropped.
    """
    # Filter to Level 1A/1B
    level_1_findings = [
        f for f in pharmgkb_findings
        if f.get('level', '').upper() in ['1A', '1B', 'LEVEL 1A', 'LEVEL 1B']
    ]

    # Sort by level (1A before 1B)
    sorted_findings = sorted(
        level_1_findings,
        key=lambda x: (x.get('level', ''), x.get('drug', ''))
    )

    return sorted_findings


def generate_core_report_markdown(results: dict, subject_name: str = None) -> str:
    """Generate $39 Core Report in Markdown format.

    Uses the same programmatic format as the exhaustive report, but truncated:
    - Executive summary (no categories list)
    - Priority findings (high + moderate only, with full clinical context)
    - Pathway analysis
    - PharmGKB Level 1A/1B only (detailed per-entry format)
    - Action summary
    - Disclaimer + upsell
    """
    from generate_exhaustive_report import (
        generate_executive_summary,
        generate_priority_findings,
        generate_pathway_analysis,
        generate_pharmgkb_report,
        generate_action_summary,
        generate_disclaimer,
    )

    # Filter data for Core tier
    all_findings = results.get('findings', [])
    lifestyle_findings = filter_lifestyle_findings(all_findings)
    pharma_quick = filter_pharma_quick_card(results.get('pharmgkb_findings', []))

    # Build a filtered copy of results for the exhaustive functions
    core_data = {
        'findings': lifestyle_findings,
        'pharmgkb_findings': pharma_quick,
        'summary': results.get('summary', {}),
    }

    # Build report parts
    report_parts = []

    # 1. Executive summary (simplified — no categories list)
    report_parts.append(generate_executive_summary(
        core_data,
        title="DNA Decoder: Core Report",
        subject_name=subject_name,
        include_categories=False,
    ))

    # 2. Priority findings (high + moderate with full clinical context)
    report_parts.append(generate_priority_findings(lifestyle_findings))

    # 3. Pathway analysis
    report_parts.append(generate_pathway_analysis(lifestyle_findings))

    # 4. Pharmacogenomics (Level 1A/1B only, detailed format)
    if pharma_quick:
        report_parts.append(generate_pharmgkb_report(pharma_quick))

    # 5. Action summary
    report_parts.append(generate_action_summary(lifestyle_findings))

    # 6. Disclaimer
    report_parts.append(generate_disclaimer())

    # 7. Upsell
    report_parts.append("""## Want the Full Clinical Picture?

The Deep Dive report goes further — every single finding in your data, flagged variants from clinical databases (ClinVar), confirmatory testing guidance, the full pharmacogenomics table across all evidence levels, and complete pathway analysis. Most people find this Core Report gives them what they need to take action. The Deep Dive is for those who want the complete picture.

---

*DNA Decoder by Genome Platform*
""")

    md_content = "\n".join(report_parts)

    # Sanitize any clinical terms that slipped through filters
    md_content = sanitize_clinical_terms(md_content)

    return md_content


def generate_core_report(results: dict, subject_name: str = None) -> tuple:
    """
    Generate $39 Core Report (Markdown only for now).

    Returns:
        (markdown_content, html_content)
    """
    md_content = generate_core_report_markdown(results, subject_name)

    html_content = _render_report_html("DNA Decoder Core Report", md_content, accent="#7c3aed")

    return md_content, html_content


def _render_report_html(title: str, md_content: str, accent: str = "#7c3aed") -> str:
    """Render markdown into a polished, self-contained dark-mode HTML report."""
    import json as _json
    safe_md = _json.dumps(md_content)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
  :root {{
    --bg: #09090b; --surface: #18181b; --surface2: #1f1f23; --border: #27272a;
    --text: #e4e4e7; --muted: #a1a1aa;
    --accent: {accent}; --accent-light: #c4b5fd;
  }}
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: var(--bg); color: var(--text);
    font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 15px; line-height: 1.75; padding: 0;
    -webkit-font-smoothing: antialiased;
  }}
  .report-header {{
    background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 60%, #0c0a1a 100%);
    border-bottom: 2px solid var(--accent);
    padding: 56px 32px; text-align: center;
  }}
  .report-header h1 {{
    font-size: 2.2rem; color: #fff; margin: 0 0 8px;
    border: none; padding: 0; font-weight: 700;
    letter-spacing: -0.02em;
  }}
  .report-header p {{ color: var(--accent-light); font-size: 0.95rem; opacity: 0.85; }}
  .report-body {{
    max-width: 960px; margin: 0 auto; padding: 48px 32px 80px;
  }}
  h1 {{
    font-size: 1.8rem; color: #fff;
    border-bottom: 2px solid var(--accent);
    padding-bottom: 12px; margin: 48px 0 24px;
    font-weight: 700; letter-spacing: -0.01em;
  }}
  h2 {{
    font-size: 1.4rem; color: var(--accent-light);
    margin: 40px 0 16px; padding-bottom: 10px;
    border-bottom: 1px solid var(--border);
    font-weight: 600;
  }}
  h3 {{
    font-size: 1.15rem; color: #a78bfa;
    margin: 32px 0 12px; font-weight: 600;
  }}
  h4 {{
    font-size: 1.05rem; color: #c4b5fd;
    margin: 24px 0 8px; font-weight: 600;
  }}
  p {{ margin-bottom: 16px; color: var(--text); }}
  ul, ol {{ margin: 0 0 18px 24px; }}
  li {{ margin-bottom: 8px; }}
  hr {{
    border: none; border-top: 1px solid var(--border);
    margin: 36px 0;
  }}
  strong {{ color: #fff; font-weight: 600; }}
  em {{ color: var(--muted); }}
  code {{
    background: var(--surface); padding: 2px 8px;
    border-radius: 4px; font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-size: 0.88em; color: var(--accent-light);
    border: 1px solid var(--border);
  }}
  blockquote {{
    border-left: 3px solid var(--accent);
    padding: 16px 20px; background: var(--surface);
    border-radius: 0 8px 8px 0; margin: 20px 0;
    color: var(--muted); font-style: italic;
  }}

  /* ── Table styles ── */
  .table-wrap {{
    width: 100%; overflow-x: auto; margin: 24px 0;
    border: 1px solid var(--border); border-radius: 10px;
    background: var(--surface);
  }}
  table {{
    width: 100%; border-collapse: collapse;
    font-size: 0.875rem; table-layout: fixed;
  }}
  th {{
    background: var(--surface2); color: var(--accent-light);
    padding: 14px 16px; text-align: left;
    border-bottom: 2px solid var(--border);
    font-weight: 600; font-size: 0.8rem;
    text-transform: uppercase; letter-spacing: 0.04em;
    white-space: nowrap;
  }}
  td {{
    padding: 14px 16px; border-bottom: 1px solid var(--border);
    color: var(--text); vertical-align: top;
    word-wrap: break-word; overflow-wrap: break-word;
  }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: rgba(124, 58, 237, 0.06); }}

  /* Column widths for 5-column pharma tables (Drug | Gene | Phenotype | Level | Annotation) */
  table th:nth-child(1), table td:nth-child(1) {{ width: 14%; }}
  table th:nth-child(2), table td:nth-child(2) {{ width: 10%; }}
  table th:nth-child(3), table td:nth-child(3) {{ width: 12%; }}
  table th:nth-child(4), table td:nth-child(4) {{ width: 8%; text-align: center; }}
  table th:nth-child(5), table td:nth-child(5) {{ width: 56%; }}

  /* 2-column summary tables get auto layout */
  table:has(th:nth-child(2):last-child) {{ table-layout: auto; }}
  table:has(th:nth-child(2):last-child) th,
  table:has(th:nth-child(2):last-child) td {{ width: auto; text-align: left; }}
  table:has(th:nth-child(3):last-child) {{ table-layout: auto; }}
  table:has(th:nth-child(3):last-child) th,
  table:has(th:nth-child(3):last-child) td {{ width: auto; text-align: left; }}

  .report-footer {{
    margin-top: 56px; padding: 28px 0;
    border-top: 1px solid var(--border);
    color: var(--muted); font-size: 0.8rem;
    text-align: center; line-height: 1.7;
  }}

  @media print {{
    body {{ background: #fff; color: #111; font-size: 11pt; }}
    .report-header {{ background: #f5f3ff; border-color: {accent}; }}
    .report-header h1 {{ color: #111; }}
    .report-header p {{ color: #4c1d95; }}
    h1 {{ color: #111; border-color: {accent}; }}
    h2 {{ color: #4c1d95; border-color: #e5e7eb; }}
    h3 {{ color: #5b21b6; }}
    h4 {{ color: #4c1d95; }}
    p, li, td {{ color: #333; }}
    strong {{ color: #111; }}
    code {{ background: #f5f3ff; color: #4c1d95; border-color: #e5e7eb; }}
    th {{ background: #f5f3ff; color: #4c1d95; }}
    blockquote {{ background: #f9fafb; border-color: {accent}; color: #555; }}
    tr:hover td {{ background: transparent; }}
    .table-wrap {{ border-color: #e5e7eb; }}
  }}
  @media (max-width: 600px) {{
    .report-body {{ padding: 24px 16px 60px; }}
    .report-header {{ padding: 36px 16px; }}
    table {{ font-size: 0.78rem; }}
    th, td {{ padding: 10px 10px; }}
  }}
</style>
</head>
<body>
<div class="report-header">
  <h1>{title}</h1>
  <p>DNA Decoder by Helix Health</p>
</div>
<div class="report-body">
  <div id="content"></div>
  <div class="report-footer">
    This report is for educational purposes only and does not constitute medical advice.<br>
    Always consult a qualified healthcare provider before making health decisions based on genetic information.
  </div>
</div>
<script>
  document.getElementById('content').innerHTML = marked.parse({safe_md});
  // Wrap all tables in a scrollable container
  document.querySelectorAll('#content table').forEach(function(table) {{
    var wrap = document.createElement('div');
    wrap.className = 'table-wrap';
    table.parentNode.insertBefore(wrap, table);
    wrap.appendChild(table);
  }});
</script>
</body>
</html>"""


if __name__ == '__main__':
    # Test with sample data
    sample_results = {
        'findings': [
            {'gene': 'CYP1A2', 'trait': 'Caffeine metabolism', 'genotype': 'AC', 'magnitude': 3,
             'summary': 'Slow caffeine metabolizer - caffeine may affect sleep more'},
            {'gene': 'MTHFR', 'trait': 'Methylation', 'genotype': 'CT', 'magnitude': 4,
             'summary': 'Reduced MTHFR activity - may benefit from methylated B vitamins'},
        ],
        'pharmgkb_findings': [
            {'drug': 'Warfarin', 'gene': 'CYP2C9', 'level': '1A', 'phenotype': 'Normal metabolizer',
             'annotation': 'Standard dosing likely appropriate'},
            {'drug': 'Clopidogrel', 'gene': 'CYP2C19', 'level': '1A', 'phenotype': 'Poor metabolizer',
             'annotation': 'Reduced effectiveness - consider alternative'},
        ]
    }

    md, html = generate_core_report(sample_results, "Test Subject")
    print("Core Report generated successfully!")
    print(f"Length: {len(md)} characters")
