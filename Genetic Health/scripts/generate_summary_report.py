"""
Master Summary Report Generator

Calls the OpenAI API to produce a plain-English, 9th-grade-level summary
of all genome analysis results — designed for non-medical, non-technical readers.
"""

import json
import os
from pathlib import Path


def generate_summary_report(results: dict, subject_name: str | None = None) -> str:
    """
    Takes the comprehensive_results.json dict and generates a warm, plain-English
    master summary report using OpenAI.

    Args:
        results: dict loaded from comprehensive_results.json
        subject_name: optional name to personalize the report

    Returns:
        Markdown string of the full summary report
    """
    from openai import OpenAI

    name = subject_name or "You"
    first_name = name.split()[0] if name and name != "You" else "You"

    findings = results.get("findings", [])
    pharmgkb = results.get("pharmgkb_findings", [])
    summary = results.get("summary", {})

    # Group findings by confidence tier
    high_conf = sorted(
        [f for f in findings if f.get("magnitude", 0) >= 3],
        key=lambda x: x.get("magnitude", 0), reverse=True,
    )
    med_conf = sorted(
        [f for f in findings if f.get("magnitude", 0) == 2],
        key=lambda x: x.get("magnitude", 0), reverse=True,
    )
    low_conf = [f for f in findings if f.get("magnitude", 0) == 1]

    def _fmt_finding(f):
        return (f"- Gene: {f['gene']} | Category: {f.get('category','')} | "
                f"Status: {f.get('status','')} | Effect: {f.get('description','')} | "
                f"Magnitude: {f.get('magnitude',0)}/6")

    findings_text = ""
    if high_conf:
        findings_text += "HIGH-CONFIDENCE FINDINGS (magnitude 3+):\n"
        findings_text += "\n".join(_fmt_finding(f) for f in high_conf[:5]) + "\n\n"
    if med_conf:
        findings_text += "MODERATE-CONFIDENCE FINDINGS (magnitude 2):\n"
        findings_text += "\n".join(_fmt_finding(f) for f in med_conf[:5]) + "\n\n"
    if low_conf:
        findings_text += "PRELIMINARY FINDINGS (magnitude 1, limited evidence):\n"
        findings_text += "\n".join(_fmt_finding(f) for f in low_conf[:3]) + "\n"
    if not findings_text:
        findings_text = "No significant findings."

    # Pull Level 1 pharma interactions
    level1_pharma = [
        p for p in pharmgkb if p.get("level", "").startswith("1")
    ][:5]

    pharma_text = "\n".join(
        f"- Gene: {p['gene']} | Drugs affected: {p.get('drug', '') or p.get('drugs','')} | "
        f"Clinical note: {(p.get('annotation','') or '')[:200]}"
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

HEALTH FINDINGS (grouped by confidence level):
{findings_text}

MEDICATION-GENE INTERACTIONS (Level 1 evidence only):
{pharma_text}

Please write the full Master Summary Report now following the exact structure and tone specified.
""".strip()

    system_prompt = """You are a direct, no-BS genetics interpreter. You speak in plain English.
Short sentences. No fluff. No corporate filler. No hand-holding.
You give people the actual information, not descriptions of what each section means.
You are blunt but not cruel. You use analogies and metaphors to make complex things click.
Never make a medical diagnosis. Say "talk to your doctor" when relevant, but don't drown the report in disclaimers.

Your tone examples:
- "These are genetic maybes, not diagnoses."
- "Think of these as dials, not switches. Lifestyle turns the dial way more than these SNPs do."
- "If someone with your profile lives like trash, problems show up faster. If they live intentionally, they often outperform averages."
- "This is monitoring territory, not alarm territory."

Write the report in Markdown with these exact sections:

# Your DNA, Decoded
## The plain English version. No fluff.

---

## The Big Picture
[3-5 sentences. Lead with the single most important takeaway — do they have confirmed genetic diseases or not? Then state key counts: how many variants analyzed, how many meaningful findings, how many are actually worth paying attention to. No filler. Be direct.]

---

## What Your Genetics Actually Show

[DO NOT explain what each section means. Give the actual information. For each significant finding:]

[For high-confidence findings: State what the gene does, what their variant means in practice, and one concrete implication for their life. 2-3 sentences max per finding. No headers per gene — use bold gene name inline.]

[For moderate findings: Same format but shorter. Note evidence is still developing.]

[For preliminary findings: One-line bullet points only. Frame as "early research suggests..." Keep it tight.]

[After listing findings, add a "Translation:" line that cuts through the jargon in one punchy sentence.]

---

## How Your Body Handles Medications
[This is the sleeper gold section. Be direct about what it means for them. List specific drug categories affected and why. Use "you likely..." language. End with: "Always mention you have pharmacogenomic variants before starting long-term meds."]

---

## What to Actually Do
[Specific actionable list based on their findings. Split into Daily / Weekly / Avoid subsections. Include supplements that align with their profile. These should be tied to actual findings, not generic wellness advice.]

---

## Red Flags to Watch For
[Symptom watchlist grouped by category (metabolic, circulation, inflammation, etc.). These are early warning lights, not panic signals. Be specific about what symptoms matter and when to act.]

---

## The Bottom Line
[3-5 punchy sentences. No genetic diseases detected (if true). Main risk clusters. Lifestyle leverage. End with something like: "Your genes do not doom you to anything. You are highly responsive to both good choices and bad ones. That is not a weakness. It is leverage."]

---

*This report is for educational purposes only. It is not a diagnosis. Talk to your doctor before making health decisions based on genetic data.*"""

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    response = client.chat.completions.create(
        model="gpt-5-nano",
        max_tokens=4096,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    return response.choices[0].message.content
