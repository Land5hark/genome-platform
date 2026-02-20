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


def assert_no_clinical_terms(content: str):
    """Assert that Core Report does NOT contain forbidden clinical terms."""
    content_lower = content.lower()

    for term in FORBIDDEN_CLINICAL_TERMS:
        if term in content_lower:
            raise ValueError(
                f"VIOLATION: Core Report contains forbidden term: '{term}'. "
                f"This term must only appear in the Deep Dive report."
            )


def filter_lifestyle_findings(findings: list) -> list:
    """
    Filter findings to ONLY include lifestyle genetics categories.

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

        if is_lifestyle:
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

    # Assert no forbidden terms
    assert_no_clinical_terms(md_content)

    return md_content


def generate_core_report(results: dict, subject_name: str = None) -> tuple:
    """
    Generate $39 Core Report (Markdown only for now).

    Returns:
        (markdown_content, html_content)
    """
    md_content = generate_core_report_markdown(results, subject_name)

    # For soft launch, HTML is same as MD (browser will render)
    # We can add proper HTML styling later
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DNA Decoder Core Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; line-height: 1.6; }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background: #3498db; color: white; }}
        .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }}
        .info {{ background: #d1ecf1; border-left: 4px solid #17a2b8; padding: 15px; margin: 20px 0; }}
    </style>
</head>
<body>
<pre style="white-space: pre-wrap; font-family: Arial, sans-serif;">
{md_content}
</pre>
</body>
</html>
"""

    return md_content, html_content


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
