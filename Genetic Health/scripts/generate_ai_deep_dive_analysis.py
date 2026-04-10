"""
AI-Powered Deep Dive Analysis via OpenRouter (Nemotron)

Synthesizes all genetic layers — lifestyle, pharmacogenomics, ClinVar —
into a personalized narrative section for the Deep Dive report.
"""

import os
import logging

logger = logging.getLogger(__name__)

OPENROUTER_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def generate_ai_analysis(
    results: dict,
    pathogenic_variants: list,
    subject_name: str | None = None,
) -> str:
    """
    Call OpenRouter (Nemotron) to generate an AI narrative analysis section.

    Args:
        results: dict from comprehensive_results.json
        pathogenic_variants: list of pathogenic variants from extract_pathogenic_variants()
        subject_name: optional name to personalize the report

    Returns:
        Markdown string for the AI Clinical Intelligence section,
        or empty string if the call fails.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        logger.warning("OPENROUTER_API_KEY not set — skipping AI analysis section")
        return ""

    from openai import OpenAI

    name = subject_name or "the subject"
    first_name = name.split()[0] if name and name not in ("the subject", "You") else "You"

    findings = results.get("findings", [])
    pharmgkb = results.get("pharmgkb_findings", [])
    summary = results.get("summary", {})
    disease_stats = results.get("disease_stats", {})

    # Top lifestyle findings
    high_findings = sorted(
        [f for f in findings if f.get("magnitude", 0) >= 3],
        key=lambda x: x.get("magnitude", 0), reverse=True,
    )[:8]
    med_findings = sorted(
        [f for f in findings if f.get("magnitude", 0) == 2],
        key=lambda x: x.get("magnitude", 0), reverse=True,
    )[:5]

    def _fmt(f):
        return (
            f"- {f.get('gene', '?')} | {f.get('category', '')} | "
            f"{f.get('status', '')} | {(f.get('description', '') or '')[:150]}"
        )

    findings_text = ""
    if high_findings:
        findings_text += "HIGH IMPACT:\n" + "\n".join(_fmt(f) for f in high_findings) + "\n\n"
    if med_findings:
        findings_text += "MODERATE IMPACT:\n" + "\n".join(_fmt(f) for f in med_findings) + "\n\n"
    if not findings_text:
        findings_text = "No notable lifestyle/wellness findings detected.\n"

    # PharmGKB Level 1 interactions
    top_pharma = [p for p in pharmgkb if p.get("level", "").startswith("1")][:6]
    pharma_text = "\n".join(
        f"- {p.get('gene', '?')} | {p.get('drug', '')} | "
        f"Level {p.get('level', '')} | {(p.get('annotation', '') or '')[:120]}"
        for p in top_pharma
    ) or "No Level 1 drug-gene interactions detected."

    # ClinVar clinical variants
    if pathogenic_variants:
        clinvar_text = "\n".join(
            f"- {v['gene']} ({v['significance'].replace('_', ' ')}) | "
            f"{v['condition'].split(';')[0]} | "
            f"Confidence: {v['confidence']}/4 | "
            f"{'Homozygous' if v['is_homozygous'] else 'Heterozygous'}"
            for v in pathogenic_variants[:10]
        )
    else:
        clinvar_text = "No pathogenic or likely pathogenic ClinVar variants detected."

    total_snps = summary.get("total_snps", 0)
    high_impact_count = summary.get("high_impact", 0)
    pathogenic_count = disease_stats.get("pathogenic_matched", 0)

    user_prompt = f"""Subject: {name}
Total SNPs analyzed: {total_snps:,}
High-impact lifestyle findings: {high_impact_count}
ClinVar pathogenic variants: {pathogenic_count}

LIFESTYLE & WELLNESS GENETICS:
{findings_text}
MEDICATION-GENE INTERACTIONS (Level 1 evidence):
{pharma_text}

CLINVAR CLINICAL VARIANTS:
{clinvar_text}

Write the AI Clinical Intelligence section now."""

    system_prompt = f"""You are a direct, no-BS genetics analyst. You synthesize all genetic layers — lifestyle, clinical, pharmacogenomics — into one cohesive narrative.

Write for someone smart but not medical. Short sentences. No corporate filler. No hand-holding.
Give real information, not descriptions of what each section means.

Tone examples:
- "These are genetic maybes, not diagnoses."
- "Think of these as dials, not switches. Lifestyle turns the dial way more than these SNPs do."
- "This is monitoring territory, not alarm territory."
- Blunt but not cruel. Concrete analogies when helpful.

Address {first_name} directly. Use "you" and "your".

Write ONLY these sections in Markdown — no preamble, no extra commentary:

## AI Clinical Intelligence

### The Full Picture
[3-4 sentences. What does ALL the data show together? Lead with the single most important takeaway from this entire genome — be direct about whether there are clinical concerns or not.]

### Key Genetic Patterns
[2-4 bullet points. Each is one concrete insight that connects findings across categories. No generic statements — specific to what's in this data.]

### Medication Profile
[2-3 sentences. What do the drug-gene interactions mean in practice? Which drug categories need extra attention? Be specific, not vague.]

### Clinical Flags
[If ClinVar variants were found: address them directly but non-diagnostically — "flagged" not "diagnosed". If none found: one direct sentence confirming it and why that's actually meaningful.]

### What Matters Most
[3 specific, findings-driven action items. Not generic wellness advice. Tied to what was actually found.]

---

*AI analysis generated from genomic data. Educational only — not diagnostic. Discuss findings with a qualified clinician.*"""

    try:
        client = OpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL,
        )
        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content
        return content.strip() if content else ""
    except Exception as e:
        logger.error(f"OpenRouter AI analysis failed: {e}")
        return ""
