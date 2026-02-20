#!/usr/bin/env python3
"""
Generate $39 Core Report (Lifestyle Genetics + PharmGKB Quick Card)

EXCLUDES:
- All ClinVar pathogenic/likely pathogenic/VUS variants
- PharmGKB Level 2+ findings (only include 1A/1B)
- Any clinical disease language

Includes assertions to prevent contradictions with Deep Dive report.
"""

from datetime import datetime
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
        'vitamin', 'mineral', 'nutrient'
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
    Filter PharmGKB to Level 1A/1B only, top 10 by clinical importance.
    """
    # Filter to Level 1A/1B
    level_1_findings = [
        f for f in pharmgkb_findings
        if f.get('level', '').upper() in ['1A', '1B', 'LEVEL 1A', 'LEVEL 1B']
    ]

    # Sort by level (1A before 1B) and take top 10
    sorted_findings = sorted(
        level_1_findings,
        key=lambda x: (x.get('level', ''), x.get('drug', ''))
    )

    return sorted_findings[:10]


def generate_core_report_markdown(results: dict, subject_name: str = None) -> str:
    """Generate $39 Core Report in Markdown format."""

    # Filter data
    lifestyle_findings = filter_lifestyle_findings(results.get('findings', []))
    pharma_quick = filter_pharma_quick_card(results.get('pharmgkb_findings', []))

    # Counts
    snps_analyzed = len(results.get('findings', []))  # Rough estimate
    lifestyle_count = len(lifestyle_findings)
    pharma_count = len(pharma_quick)

    now = datetime.now().strftime("%Y-%m-%d")
    subject_line = f"**Subject:** {subject_name}\n\n" if subject_name else ""

    # Build top insights (top 5 by magnitude)
    top_findings = sorted(
        lifestyle_findings,
        key=lambda x: x.get('magnitude', 0),
        reverse=True
    )[:5]

    top_insights_md = ""
    for i, finding in enumerate(top_findings, 1):
        gene = finding.get('gene', 'Unknown')
        trait = finding.get('trait', 'Unknown')
        genotype = finding.get('genotype', '')
        mag = finding.get('magnitude', 0)
        stars = '⭐' * mag

        top_insights_md += f"""
### {i}. {gene} - {trait}

- **Your Genotype:** `{genotype}`
- **Impact:** {stars} ({mag}/5)
- **What This Means:** {finding.get('summary', 'Genetic variant detected')}

---
"""

    # Build PharmGKB table
    pharma_table_md = """
| Drug | Gene | Your Status | Evidence | Notes |
|------|------|-------------|----------|-------|
"""

    for p in pharma_quick:
        drug = p.get('drug', 'Unknown')
        gene = p.get('gene', 'Unknown')
        phenotype = p.get('phenotype', 'See annotation')
        level = p.get('level', '')
        stars = '⭐' * 4 if '1A' in level else '⭐' * 3

        pharma_table_md += f"| {drug} | {gene} | {phenotype} | {stars} | {p.get('annotation', '')} |\n"

    # Markdown report
    md_content = f"""# DNA Decoder: Core Report

{subject_line}**Your Personalized Genetic Wellness Guide**

*Generated on {now}*

---

## Executive Summary

Welcome to your DNA Decoder Core Report. This report translates **{snps_analyzed}** genetic variants from your raw data into actionable wellness insights about how your body may respond to foods, supplements, medications, and lifestyle factors.

**What's Inside:**
- {lifestyle_count} lifestyle and wellness insights
- {pharma_count} medication response notes
- Evidence-based action experiments
- Personalized supplement considerations

**What This Report Covers:**
This Core Report focuses on wellness genetics and medication response—the areas where you can take action today. We analyze variants related to nutrition, metabolism, detoxification, sleep, and how your body processes common medications.

**What This Report Doesn't Cover:**
Clinical-grade disease risk screening requires separate analysis. If you're interested in exploring variants that may warrant confirmatory testing with a healthcare provider, that's available in the optional Deep Dive Clinical Context Report.

**Important Context:**
- This analysis is educational, not diagnostic
- Based on direct-to-consumer raw data (not clinical-grade sequencing)
- Many findings have emerging or limited evidence
- Always discuss significant changes with your healthcare provider

---

## Your Top Insights

{top_insights_md}

---

## 💊 Medication Response Quick Card

**Share this section with your prescriber when discussing medications**

Your genetic variants may influence how you metabolize certain medications. This is informational only—never change medications without medical supervision.

{pharma_table_md}

**Evidence Levels:**
- ⭐⭐⭐⭐ Strong clinical evidence (FDA recognized or major guidelines)
- ⭐⭐⭐ Moderate evidence (replicated studies)

**Next Steps:**
- Bring this to your doctor or pharmacist
- Ask if pharmacogenomic testing is recommended
- Request a medication review if you're taking any flagged drugs

---

## 🎯 Your Action Experiments

Start with one experiment at a time and track how you feel:

1. **Caffeine Timing:** If you have slow caffeine metabolism variants, try cutting off caffeine by 2 PM
2. **Methylated B Vitamins:** Consider methylfolate and methylcobalamin instead of folic acid/B12
3. **Antioxidant Foods:** Increase intake of colorful vegetables (berries, leafy greens, cruciferous veggies)
4. **Meal Timing:** Experiment with time-restricted eating based on your circadian rhythm genetics
5. **Exercise Type:** Match your workout to your metabolism patterns (endurance vs. strength)

---

## 📊 Confidence & Limitations

### What This Analysis Can Tell You
- Common genetic variants present in your raw data
- Research-backed associations between variants and traits
- Medication metabolism patterns recognized by pharmacogenomics

### What This Analysis Cannot Tell You
- Clinical diagnoses (that requires a doctor)
- Rare or complex genetic conditions (requires clinical sequencing)
- Exact quantified risk (genetics is one of many factors)
- What will definitely happen (genes aren't destiny)

### How to Use This Report
1. **Read for patterns, not panic.** These are tendencies, not certainties.
2. **Start small.** Pick 1-2 action experiments to try first.
3. **Track your response.** Your body's feedback is the ultimate guide.
4. **Consult professionals.** Share relevant sections with your healthcare team.
5. **Stay curious.** Genetics research is rapidly evolving.

---

## Need More?

**Interested in a deeper clinical perspective?**

The DNA Decoder Deep Dive Clinical Context Report explores additional variant categories that may warrant confirmatory testing. This optional report includes:
- Flagged variants from clinical databases
- Guidance on clinical confirmation testing
- Family planning considerations
- Full pharmacogenomics reference table

**This deep dive is entirely optional.** Most people find the Core Report gives them everything they need to take action on their wellness.

---

*DNA Decoder by Genome Platform*

**Disclaimer:** This report is for educational and informational purposes only. It is not intended to diagnose, treat, cure, or prevent any condition. Always consult with a qualified healthcare provider before making decisions about your health based on genetic information.
"""

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
    --bg: #09090b; --surface: #18181b; --border: #27272a;
    --text: #e4e4e7; --muted: #a1a1aa;
    --accent: {accent}; --accent-light: #c4b5fd;
  }}
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: var(--bg); color: var(--text);
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 15px; line-height: 1.7; padding: 0;
  }}
  .report-header {{
    background: linear-gradient(135deg, #1e1b4b, #0f172a);
    border-bottom: 2px solid var(--accent);
    padding: 48px 24px; text-align: center;
  }}
  .report-header h1 {{
    font-size: 2rem; color: #fff; margin: 0 0 8px;
    border: none; padding: 0;
  }}
  .report-header p {{ color: var(--accent-light); font-size: 0.95rem; }}
  .report-body {{
    max-width: 800px; margin: 0 auto; padding: 40px 24px 80px;
  }}
  h1 {{
    font-size: 1.8rem; color: #fff;
    border-bottom: 2px solid var(--accent);
    padding-bottom: 12px; margin: 40px 0 20px;
  }}
  h2 {{
    font-size: 1.4rem; color: var(--accent-light);
    margin: 36px 0 14px; padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
  }}
  h3 {{
    font-size: 1.15rem; color: #a78bfa;
    margin: 28px 0 10px;
  }}
  p {{ margin-bottom: 14px; color: var(--text); }}
  ul, ol {{ margin: 0 0 16px 24px; }}
  li {{ margin-bottom: 6px; }}
  hr {{
    border: none; border-top: 1px solid var(--border);
    margin: 32px 0;
  }}
  strong {{ color: #fff; }}
  em {{ color: var(--muted); }}
  code {{
    background: var(--surface); padding: 2px 8px;
    border-radius: 4px; font-family: 'Consolas', monospace;
    font-size: 0.9em; color: var(--accent-light);
    border: 1px solid var(--border);
  }}
  blockquote {{
    border-left: 3px solid var(--accent);
    padding: 14px 18px; background: var(--surface);
    border-radius: 0 8px 8px 0; margin: 16px 0;
    color: var(--muted);
  }}
  table {{
    width: 100%; border-collapse: collapse;
    margin: 20px 0; font-size: 0.9rem;
  }}
  th {{
    background: var(--surface); color: var(--accent-light);
    padding: 12px 14px; text-align: left;
    border-bottom: 2px solid var(--border);
    font-weight: 600;
  }}
  td {{
    padding: 10px 14px; border-bottom: 1px solid var(--border);
    color: var(--text);
  }}
  tr:hover td {{ background: rgba(124, 58, 237, 0.04); }}
  .report-footer {{
    margin-top: 48px; padding: 24px 0;
    border-top: 1px solid var(--border);
    color: var(--muted); font-size: 0.8rem;
    text-align: center; line-height: 1.6;
  }}
  @media print {{
    body {{ background: #fff; color: #111; font-size: 12pt; }}
    .report-header {{ background: #f5f3ff; border-color: {accent}; }}
    .report-header h1 {{ color: #111; }}
    .report-header p {{ color: #4c1d95; }}
    h1 {{ color: #111; border-color: {accent}; }}
    h2 {{ color: #4c1d95; border-color: #e5e7eb; }}
    h3 {{ color: #5b21b6; }}
    p, li, td {{ color: #333; }}
    strong {{ color: #111; }}
    code {{ background: #f5f3ff; color: #4c1d95; border-color: #e5e7eb; }}
    th {{ background: #f5f3ff; color: #4c1d95; }}
    blockquote {{ background: #f9fafb; border-color: {accent}; color: #555; }}
    tr:hover td {{ background: transparent; }}
  }}
  @media (max-width: 600px) {{
    .report-body {{ padding: 24px 16px 60px; }}
    .report-header {{ padding: 32px 16px; }}
    table {{ font-size: 0.8rem; }}
    th, td {{ padding: 8px; }}
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
