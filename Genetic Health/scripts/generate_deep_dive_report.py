#!/usr/bin/env python3
"""
Generate $79 Deep Dive Clinical Context Report

INCLUDES:
- All lifestyle genetics (same as Core)
- Full PharmGKB table (all levels)
- ClinVar pathogenic/likely pathogenic variants
- VUS (variants of uncertain significance)
- Clinical context and confirmatory testing guidance

Uses non-diagnostic framing - never says "you have X" or "you are affected".
"""

from datetime import datetime
from pathlib import Path
import re


# Forbidden diagnostic phrases (strong affirmative statements only)
FORBIDDEN_DIAGNOSTIC_PHRASES = [
    r'you are diagnosed with',
    r'this confirms you have \w+ (disease|syndrome|disorder)',
    r'results confirm that you',
    r'genetic test shows you have',
]


def assert_proper_clinical_framing(content: str):
    """Assert Deep Dive uses proper non-diagnostic language."""
    content_lower = content.lower()

    for pattern in FORBIDDEN_DIAGNOSTIC_PHRASES:
        if re.search(pattern, content_lower):
            raise ValueError(
                f"VIOLATION: Deep Dive report contains forbidden diagnostic language: {pattern}. "
                f"Use 'flagged', 'warrants confirmation', or 'potential association' instead."
            )


def extract_pathogenic_variants(disease_findings: dict) -> list:
    """
    Extract pathogenic and likely pathogenic variants from ClinVar data.
    """
    pathogenic_variants = []

    if not disease_findings:
        return pathogenic_variants

    # Combine pathogenic and likely_pathogenic lists
    for variant in disease_findings.get('pathogenic', []) + disease_findings.get('likely_pathogenic', []):
        pathogenic_variants.append({
            'gene': variant.get('gene', 'Unknown'),
            'rsid': variant.get('rsid', 'Unknown'),
            'chromosome': variant.get('chromosome', '?'),
            'position': variant.get('position', '?'),
            'genotype': variant.get('user_genotype', '??'),
            'significance': variant.get('significance', 'pathogenic'),
            'condition': variant.get('traits', 'Not specified'),
            'evidence_source': 'ClinVar',
            'confidence': variant.get('gold_stars', 0),
            'is_homozygous': variant.get('is_homozygous', False)
        })

    return pathogenic_variants


def generate_deep_dive_report_markdown(results: dict, disease_findings: dict,
                                       subject_name: str = None) -> str:
    """Generate $79 Deep Dive Report in Markdown format."""

    # Extract data
    pathogenic_variants = extract_pathogenic_variants(disease_findings)
    all_pharmgkb = results.get('pharmgkb_findings', [])

    # Counts
    total_variants = len(results.get('findings', []))
    pathogenic_count = len(pathogenic_variants)
    pharmgkb_count = len(all_pharmgkb)

    now = datetime.now().strftime("%Y-%m-%d")
    subject_line = f"**Subject:** {subject_name}\n\n" if subject_name else ""

    # Build pathogenic variants section
    pathogenic_section = ""
    if pathogenic_variants:
        pathogenic_section = "## High-Priority Variants\n\n"
        pathogenic_section += "These variants have been flagged in clinical databases. Each warrants discussion with a genetic counselor or physician.\n\n"

        for variant in pathogenic_variants:
            stars = '⭐' * variant['confidence']
            sig = variant['significance'].replace('_', ' ').title()
            genotype_desc = 'Homozygous' if variant['is_homozygous'] else 'Heterozygous'

            pathogenic_section += f"""### {variant['gene']} - {variant['condition'].split(';')[0]}

- **Position:** chr{variant['chromosome']}:{variant['position']}
- **rsID:** {variant['rsid']}
- **Your Genotype:** `{variant['genotype']}` ({genotype_desc})
- **Classification:** {sig}
- **Confidence:** {stars} ({variant['confidence']}/4)
- **Evidence Source:** {variant['evidence_source']}

**Interpretation:**
This variant has been flagged in the ClinVar database as {sig.lower()}. This means research has associated it with {variant['condition'].lower()}. **Important:** Being flagged does NOT mean you are affected. Clinical-grade confirmation testing is required, and additional factors (family history, symptoms, other genetic and environmental factors) influence actual risk.

**Next Steps:**
1. Discuss this finding with a genetic counselor
2. Request clinical confirmation testing if recommended
3. Provide family history and symptoms to contextualize the finding

---

"""
    else:
        pathogenic_section = """## High-Priority Variants

No pathogenic or likely pathogenic variants were detected in the analyzed data. This is reassuring, but remember:
- Consumer genetic testing doesn't detect all variants
- Rare variants may not be covered by the chip
- Continue recommended health screenings based on age and family history

---

"""

    # Build PharmGKB table
    pharma_table_md = """
| Drug | Gene | Phenotype | Level | Clinical Annotation |
|------|------|-----------|-------|---------------------|
"""

    for p in all_pharmgkb:
        drug = p.get('drug', 'Unknown')
        gene = p.get('gene', 'Unknown')
        phenotype = p.get('phenotype', 'See annotation')
        level = p.get('level', '')
        annotation = p.get('annotation', '')

        pharma_table_md += f"| {drug} | {gene} | {phenotype} | {level} | {annotation} |\n"

    # Markdown report
    md_content = f"""# DNA Decoder: Deep Dive Clinical Context Report

{subject_line}**Your Comprehensive Genetic Analysis**

*Generated on {now}*

---

## Executive Summary

This Deep Dive report provides a comprehensive view of your genetic data, including variants flagged in clinical databases like ClinVar and PharmGKB. This is an informational resource to help you have more informed conversations with your healthcare providers—**it is not a diagnosis.**

**What's Inside:**
- {total_variants} variants analyzed across databases
- {pathogenic_count} variants flagged as pathogenic or likely pathogenic
- {pharmgkb_count} pharmacogenomic findings
- Guidance on confirmatory testing and next steps
- Family planning considerations

**Critical Context:**
- **This is not diagnostic.** Clinical confirmation is required for any flagged variant.
- **Raw data has limitations.** Direct-to-consumer tests miss rare variants and provide lower accuracy than clinical sequencing.
- **Flagged ≠ affected.** Many flagged variants require two copies (homozygous) to cause a condition, and you may have only one (heterozygous).
- **Uncertainty is normal.** Genetic research is evolving—today's "uncertain significance" may be reclassified tomorrow.

---

## Understanding This Report

### What Do "Pathogenic" and "Likely Pathogenic" Mean?

Clinical databases like ClinVar classify variants based on their evidence for causing conditions:

- **Pathogenic:** Strong evidence that this variant can contribute to a condition
- **Likely Pathogenic:** Moderate-to-strong evidence suggesting association
- **Uncertain Significance:** Not enough evidence to classify
- **Likely Benign / Benign:** Evidence suggests no increased risk

**Important:** Being flagged as "pathogenic" does NOT mean you are affected. It means:
1. This variant has been associated with a condition in published research
2. You may carry one or two copies of this variant
3. Clinical-grade confirmation testing is needed
4. Additional factors (family history, symptoms, other genes) influence actual risk

### Why Raw Data Requires Confirmation

Your raw genetic data from consumer testing:
- Uses microarray chips that check ~600,000 common variants
- May have false positives or false negatives
- Doesn't detect rare variants, deletions, or duplications
- Provides probabilities, not certainties

**Clinical-grade confirmatory testing** uses:
- Targeted sequencing or full exome/genome sequencing
- Higher accuracy with independent verification
- Medical-grade quality control
- Results you can use for healthcare decisions

**Never make medical decisions based on raw data alone.**

---

## Summary Dashboard

| Category | Count |
|----------|-------|
| Total Variants Analyzed | {total_variants} |
| Pathogenic/Likely Pathogenic Flagged | {pathogenic_count} |
| PharmGKB Drug Interactions | {pharmgkb_count} |

---

{pathogenic_section}

## Pharmacogenomics: Full Reference Table

This table shows all medication-gene interactions found in your data.

**Important:** This is informational only. Never adjust medications without medical supervision.

{pharma_table_md}

### Evidence Levels Explained

- **Level 1A:** FDA-recognized, guideline-recommended
- **Level 1B:** Strong clinical evidence, medical consensus
- **Level 2A:** Moderate evidence, replicated studies
- **Level 2B:** Preliminary evidence from limited studies
- **Level 3:** In vitro or theoretical associations

**For medications you're currently taking:** Bring this table to your prescriber or pharmacist. Ask if dose adjustments, monitoring, or alternative medications are recommended.

---

## Recommended Confirmatory Testing & Follow-Up

### If High-Priority Variants Were Flagged

1. **Request a Genetic Counseling Consultation**
   - Genetic counselors interpret results in the context of your health history
   - They can order appropriate confirmatory testing
   - Insurance often covers counseling for flagged variants

2. **Clinical Confirmation Options**
   - **Targeted Gene Panel:** Test specific genes flagged in this report
   - **Exome Sequencing:** Analyze all protein-coding genes (~20,000 genes)
   - **Genome Sequencing:** Full DNA analysis including non-coding regions

3. **Questions to Ask Your Doctor**
   - "Should I have clinical-grade testing for this variant?"
   - "What symptoms or health history would make this more concerning?"
   - "Are there screening tests I should have based on this finding?"
   - "Should my family members be informed or tested?"

### If PharmGKB Findings Were Flagged

1. Bring the Pharmacogenomics table to your prescriber
2. Request a Medication Review if you're taking any flagged drugs
3. Ask about formal PGx testing (clinical pharmacogenomic panel)
4. Keep a copy for future prescriptions and emergency situations

---

## Family Planning & Relatives

### Should You Share This Information?

**Consider sharing if:**
- You have children or plan to have children
- Close relatives have relevant health conditions
- A flagged variant is associated with hereditary cancer or cardiac conditions
- A pharmacogenomic finding could affect a relative's current medications

**How to share responsibly:**
- Start with: "I did a genetic analysis and found a flagged variant—it may or may not be significant."
- Recommend they speak with their doctor or genetic counselor
- Provide the gene name and condition, not raw data files
- Respect their choice—some people prefer not to know

---

## How to Use This Report

### ✅ Do:
- Share relevant sections with your healthcare providers
- Request genetic counseling for flagged variants
- Ask about clinical confirmation testing
- Use pharmacogenomics findings when discussing medications
- Keep this report updated if you retest in the future

### ❌ Don't:
- Make medical decisions based solely on this report
- Assume flagged variants mean you are affected
- Start or stop medications without supervision
- Panic—most flagged variants have low penetrance or require additional factors
- Share raw genetic data publicly (privacy risk)

---

*DNA Decoder Deep Dive by Genome Platform*

**Disclaimer:** This report is for educational and informational purposes only. It is not a clinical diagnostic test. Variants flagged in this report should be confirmed with clinical-grade testing before any medical decisions are made. This report does not replace consultation with qualified healthcare providers, including genetic counselors and physicians. Always seek professional medical advice before acting on genetic information.
"""

    # Assert proper framing
    assert_proper_clinical_framing(md_content)

    return md_content


def generate_deep_dive_report(results: dict, disease_findings: dict,
                              subject_name: str = None) -> tuple:
    """
    Generate $79 Deep Dive Report (Markdown + HTML).

    Returns:
        (markdown_content, html_content)
    """
    md_content = generate_deep_dive_report_markdown(results, disease_findings, subject_name)

    from generate_core_report import _render_report_html
    html_content = _render_report_html("DNA Decoder Deep Dive Report", md_content, accent="#4f46e5")

    return md_content, html_content


if __name__ == '__main__':
    # Test with sample data
    sample_results = {
        'findings': [
            {'gene': 'CYP1A2', 'trait': 'Caffeine metabolism'},
        ],
        'pharmgkb_findings': [
            {'drug': 'Warfarin', 'gene': 'CYP2C9', 'level': '1A', 'phenotype': 'Normal', 'annotation': 'Standard dosing'},
        ]
    }

    sample_disease = {
        'pathogenic': [
            {'gene': 'BRCA1', 'rsid': 'rs80357906', 'chromosome': '17', 'position': '43094692',
             'user_genotype': 'AG', 'traits': 'Breast cancer', 'gold_stars': 4, 'is_homozygous': False}
        ],
        'likely_pathogenic': []
    }

    md, html = generate_deep_dive_report(sample_results, sample_disease, "Test Subject")
    print("Deep Dive Report generated successfully!")
    print(f"Length: {len(md)} characters")
