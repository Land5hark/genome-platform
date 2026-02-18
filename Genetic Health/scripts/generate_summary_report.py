"""
Master Summary Report Generator

Calls the Anthropic API to produce a plain-English, 9th-grade-level summary
of all genome analysis results — designed for non-medical, non-technical readers.
"""

import json
import os
from pathlib import Path


def generate_summary_report(results: dict, subject_name: str | None = None) -> str:
    """
    Takes the comprehensive_results.json dict and generates a warm, plain-English
    master summary report using Claude.

    Args:
        results: dict loaded from comprehensive_results.json
        subject_name: optional name to personalize the report

    Returns:
        Markdown string of the full summary report
    """
    import anthropic

    name = subject_name or "You"
    first_name = name.split()[0] if name and name != "You" else "You"

    findings = results.get("findings", [])
    pharmgkb = results.get("pharmgkb_findings", [])
    summary = results.get("summary", {})

    # Pull high-impact findings (magnitude >= 2)
    high_findings = sorted(
        [f for f in findings if f.get("magnitude", 0) >= 2],
        key=lambda x: x.get("magnitude", 0),
        reverse=True,
    )[:10]

    # Pull Level 1 pharma interactions
    level1_pharma = [
        p for p in pharmgkb if p.get("level", "").startswith("1")
    ][:5]

    # Build a structured prompt input
    findings_text = "\n".join(
        f"- Gene: {f['gene']} | Category: {f.get('category','')} | "
        f"Status: {f.get('status','')} | Effect: {f.get('description','')} | "
        f"Magnitude: {f.get('magnitude',0)}/6"
        for f in high_findings
    ) or "No high-impact findings."

    pharma_text = "\n".join(
        f"- Gene: {p['gene']} | Drugs affected: {p.get('drugs','')} | "
        f"Clinical note: {p.get('annotation','')[:200]}"
        for p in level1_pharma
    ) or "No Level 1 drug-gene interactions found."

    # Disease risk counts from summary-level data if available
    disease_stats = results.get("disease_stats", {})
    pathogenic_count = disease_stats.get("pathogenic_matched", 0)
    risk_factor_count = disease_stats.get("matched", 0) - pathogenic_count

    user_prompt = f"""
Subject name: {name}

GENOME ANALYSIS SUMMARY STATISTICS:
- Total SNPs analyzed: {summary.get('total_snps', 'unknown'):,}
- Variants matched to health database: {summary.get('analyzed_snps', 0)}
- High-impact findings: {summary.get('high_impact', 0)}
- Moderate-impact findings: {summary.get('moderate_impact', 0)}
- Pathogenic/likely-pathogenic disease variants: {pathogenic_count}
- Risk factor variants: {risk_factor_count}

TOP HEALTH FINDINGS (ordered by significance):
{findings_text}

MEDICATION-GENE INTERACTIONS (Level 1 evidence only):
{pharma_text}

Please write the full Master Summary Report now following the exact structure and tone specified.
""".strip()

    system_prompt = """You are a warm, friendly health educator writing a personal genetic summary report.
Your reader has no medical or science background. Write at a clear 9th-grade reading level.
Use short sentences. Explain every term you use. Be encouraging and empowering, never alarming.
Never make a medical diagnosis. Always recommend consulting a doctor for any medical decisions.

Write the report in Markdown with these exact sections:

# Your Personal Genome Summary
## A Plain-English Guide to What Your DNA Is Telling You

---

## Your Genome at a Glance
[3-4 sentence overview. Mention total variants analyzed, number of meaningful findings, and give a warm reassuring framing. Make the reader feel excited, not scared.]

---

## Your Top Health Insights
[One subsection per high-impact finding. For each:
- Use a friendly heading like "### Your [GENE] Gene"
- 2-3 paragraphs: what the gene does in plain English, what your specific variant means, and why it matters for daily life
- End each with 1 specific question it raises that the full report answers]

---

## Medications & Your Genes
[Plain summary of drug-gene interactions found. If none, say so warmly. Explain what pharmacogenomics means in one sentence. For each interaction, say which drug category is affected and why that's worth knowing — without alarm.]

---

## What Might Be Worth Watching
[Disease risk factors explained simply. Use phrases like "your DNA suggests a slightly higher chance" not "you have X disease". Focus on empowerment: these are things worth being aware of and discussing with a doctor. Never be alarmist.]

---

## Simple Steps That Could Help
[Top 5 actionable suggestions in plain English — supplements, diet tweaks, lifestyle changes — based on the findings. Write these as friendly tips, not medical prescriptions. Number them 1-5.]

---

## What This Report Doesn't Tell You
[2-3 paragraphs: honest, warm disclaimer. DNA is one piece of the puzzle. Lifestyle matters. Please talk to a doctor. This is for educational purposes only.]

---
*This summary was prepared using genetic data analysis. It is for educational purposes only and does not constitute medical advice.*"""

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return message.content[0].text
