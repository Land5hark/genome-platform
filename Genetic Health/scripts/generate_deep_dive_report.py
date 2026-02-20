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


def _build_clinvar_section(pathogenic_variants: list) -> str:
    """Build the ClinVar flagged variants section with confidence tiers."""
    pathogenic_count = len(pathogenic_variants)

    def _render_variant(variant):
        stars = '⭐' * variant['confidence']
        sig = variant['significance'].replace('_', ' ').title()
        genotype_desc = 'Homozygous (two copies)' if variant['is_homozygous'] else 'Heterozygous (one copy)'
        condition_short = variant['condition'].split(';')[0]
        return f"""**{variant['gene']}** — {condition_short}

`{variant['genotype']}` ({genotype_desc}) | {sig} | Confidence: {stars} ({variant['confidence']}/4) | {variant['rsid']} at chr{variant['chromosome']}:{variant['position']}

Research has linked this variant to {condition_short.lower()}. Flagged does not mean affected. If this truly mattered, it would likely already be obvious in your health history. Clinical confirmation testing is the only way to know for sure. Worth discussing with a genetic counselor if you have relevant family history or symptoms.

---

"""

    if not pathogenic_variants:
        return """## Flagged Variants (ClinVar)

**No pathogenic or likely pathogenic variants detected.** That is the most important line in this report.

Consumer testing does not catch everything — rare variants and structural changes are outside its scope. Keep up with age-appropriate health screenings regardless. But as far as this data goes: clear.

---

"""

    high_conf = [v for v in pathogenic_variants if v['confidence'] >= 3]
    med_conf = [v for v in pathogenic_variants if v['confidence'] == 2]
    low_conf = [v for v in pathogenic_variants if v['confidence'] <= 1]

    section = "## Flagged Variants (ClinVar)\n\n"
    section += f"Your data flagged **{pathogenic_count}** variants classified as pathogenic or likely pathogenic in clinical databases. Here is what that actually means:\n\n"
    section += "- They are flagged, not confirmed\n"
    section += "- Most are single copies, not full disease-causing pairs\n"
    section += "- Many are tied to conditions that would already be obvious if they applied to you\n"
    section += "- Clinical confirmation testing is the only way to know for sure\n\n"
    section += "Translation: These are genetic maybes, not diagnoses.\n\n---\n\n"

    if high_conf:
        section += "### High Confidence Reviews\n\nExpert-reviewed with consistent interpretation. These are the ones most worth discussing with a genetic counselor.\n\n---\n\n"
        for v in high_conf:
            section += _render_variant(v)

    if med_conf:
        section += "### Moderate Confidence Reviews\n\nMultiple reviewers, but some conflicting interpretations. Worth noting, not worth losing sleep over.\n\n---\n\n"
        for v in med_conf:
            section += _render_variant(v)

    if low_conf:
        section += "### Preliminary Reviews\n\nLimited review. Treat with extra caution — confirmatory testing matters most here.\n\n"
        for v in low_conf:
            gene = v['gene']
            condition = v['condition'].split(';')[0]
            sig = v['significance'].replace('_', ' ').title()
            genotype_desc = 'two copies' if v['is_homozygous'] else 'one copy'
            section += f"- **{gene}** ({condition}) — `{v['genotype']}` ({genotype_desc}) — {sig}\n"
        section += "\n---\n\n"

    # Jargon decoder
    section += """## Quick Jargon Decoder

You will see these terms in the findings above. Here is what they actually mean:

- **Pathogenic** — Strong research links this variant to a condition. Does not mean you are affected.
- **Likely Pathogenic** — Good evidence, not quite definitive. Same caveat.
- **Heterozygous (one copy)** — You carry one copy. Many conditions need two copies to cause problems. One copy often means carrier status at most.
- **Homozygous (two copies)** — You carry two copies. This is when it matters more. Still needs clinical confirmation.
- **ClinVar confidence stars** — How many independent reviewers agree on the classification. More stars = more reliable.

---

"""
    return section


def generate_deep_dive_report_markdown(results: dict, disease_findings: dict,
                                       subject_name: str = None) -> str:
    """Generate $79 Deep Dive Report in Markdown format.

    Uses the same programmatic format as the exhaustive report — full version:
    - Executive summary (with categories)
    - ClinVar flagged variants (confidence-tiered)
    - Priority findings (high + moderate with full clinical context)
    - Pathway analysis
    - Complete findings by category
    - Full pharmacogenomics (all evidence levels, detailed per-entry)
    - Action summary
    - Disclaimer
    """
    from generate_exhaustive_report import (
        generate_executive_summary,
        generate_priority_findings,
        generate_pathway_analysis,
        generate_full_findings,
        generate_pharmgkb_report,
        generate_action_summary,
        generate_disclaimer,
    )

    findings = results.get('findings', [])
    pharmgkb = results.get('pharmgkb_findings', [])
    pathogenic_variants = extract_pathogenic_variants(disease_findings)

    # Build report parts
    report_parts = []

    # 1. Executive summary (full — with categories)
    report_parts.append(generate_executive_summary(
        results,
        title="DNA Decoder: Deep Dive Report",
        subject_name=subject_name,
        include_categories=True,
    ))

    # 2. ClinVar flagged variants (unique to Deep Dive)
    report_parts.append(_build_clinvar_section(pathogenic_variants))

    # 3. Priority findings (high + moderate with full clinical context)
    report_parts.append(generate_priority_findings(findings))

    # 4. Pathway analysis
    report_parts.append(generate_pathway_analysis(findings))

    # 5. Complete findings by category (ALL findings)
    report_parts.append(generate_full_findings(findings))

    # 6. Full pharmacogenomics (all levels, detailed per-entry)
    if pharmgkb:
        report_parts.append(generate_pharmgkb_report(pharmgkb))

    # 7. Action summary
    report_parts.append(generate_action_summary(findings))

    # 8. Disclaimer
    report_parts.append(generate_disclaimer())

    # Footer
    report_parts.append("*DNA Decoder by Genome Platform*\n")

    md_content = "\n".join(report_parts)

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
