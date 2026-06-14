"""
AI-Powered Deep Dive Analysis via OpenRouter -> Claude Sonnet 4.6

Synthesizes all genetic layers — lifestyle, pharmacogenomics, ClinVar —
into a personalized, conversational narrative that becomes the SPINE of the
Deep Dive report. The dense template sections (tables, variant lists) become
the supporting evidence below this narrative.

Drop-in replacement: same public function signature as the original
Nemotron version, and STILL uses your existing OpenRouter key + the
OpenAI-compatible client. The only real change is the model slug and the
(much stronger) prompt.

Env:
    OPENROUTER_API_KEY   required (falls back to template-only if unset)
    DEEPDIVE_MODEL       optional override (default: anthropic/claude-sonnet-4.6)
"""

import os
import logging

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Highest-functioning / most cost-effective pick for a readable flagship
# narrative on a $79 product (~4 cents/report). Set DEEPDIVE_MODEL to
# anthropic/claude-haiku-4.5 to go cheaper, or anthropic/claude-opus-4.8 for premium.
DEFAULT_MODEL = os.environ.get("DEEPDIVE_MODEL", "anthropic/claude-sonnet-4.6")


def generate_ai_analysis(
    results: dict,
    pathogenic_variants: list,
    subject_name: str | None = None,
) -> str:
    """
    Call Claude (via OpenRouter) to generate the conversational narrative.

    Returns:
        Markdown string for the narrative section, or empty string if the
        call fails (report still renders with template sections only).
    """
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        logger.warning("OPENROUTER_API_KEY not set — skipping AI narrative section")
        return ""

    from openai import OpenAI

    name = subject_name or "the subject"
    first_name = (
        name.split()[0]
        if name and name not in ("the subject", "You")
        else "you"
    )

    findings = results.get("findings", [])
    pharmgkb = results.get("pharmgkb_findings", [])
    summary = results.get("summary", {})
    disease_stats = results.get("disease_stats", {})

    # ---- Compress the structured data into a compact brief for the model ----
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

    top_pharma = sorted(
        [p for p in pharmgkb if p.get("level", "").startswith(("1", "2"))],
        key=lambda x: x.get("level", "9"),
    )[:12]
    pharma_text = "\n".join(
        f"- {p.get('gene', '?')} | {p.get('drugs', p.get('drug', ''))} | "
        f"Level {p.get('level', '')} | {(p.get('annotation', '') or '')[:120]}"
        for p in top_pharma
    ) or "No Level 1-2 drug-gene interactions detected."

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
ClinVar pathogenic variants flagged: {pathogenic_count}

LIFESTYLE & WELLNESS GENETICS:
{findings_text}
MEDICATION-GENE INTERACTIONS (Level 1 evidence):
{pharma_text}

CLINVAR CLINICAL VARIANTS:
{clinvar_text}

Write the narrative now."""

    system_prompt = f"""You are a sharp, warm genetics translator. Your job: take a dense genomic analysis and turn it into something a smart, curious non-scientist actually wants to read — start to finish.

Write to {first_name} directly. Use "you" and "your". Second person, conversational, like a knowledgeable friend who happens to be a genetics expert explaining it over coffee. Short paragraphs. Plain words. Vary sentence length so it has rhythm.

HARD RULES — never break these (legal/clinical):
- Never write "you are diagnosed with", "this confirms you have [X] disease/syndrome/disorder", "results confirm that you", or "genetic test shows you have".
- Flagged variants are "flagged", "worth watching", "a maybe" — never "diagnosed" or "confirmed".
- Frame genetics as probabilities and dials, not destiny.

VOICE EXAMPLES (match this energy):
- "Think of these as dials, not switches. Your lifestyle moves the dial way more than these genes do."
- "These are genetic maybes, not diagnoses."
- "This is monitoring territory, not alarm territory."
- "Here's the one thing on this whole page actually worth your attention."
Blunt but kind. Concrete analogies. Zero corporate filler. Never describe what a section "will cover" — just say the actual thing.

Write ONLY the following in Markdown. No preamble, no meta-commentary.

## Your DNA, In Plain English

[2-3 short paragraphs. This is the hook and the heart of the report. Lead with the single most important takeaway from {first_name}'s ENTIRE genome — be direct about whether there's anything clinically worth attention or whether it's mostly optimization territory. Then paint the big picture: what kind of genetic profile is this? Make {first_name} feel SEEN by their own data. This section alone should be worth the price.]

### What's Actually Worth Your Attention

[3-5 bullet points, each a specific, concrete insight that connects findings across categories. No generic wellness advice. Each bullet names the real gene/pattern and what it means for {first_name} in practice. Order by what matters most.]

### Your Medication Profile

[2-3 sentences. What do the drug-gene interactions mean the next time {first_name} gets a prescription? Name the specific drug categories that need extra care — if opioid or pain medication interactions are present, always name them explicitly. If nothing notable, say so plainly and move on.]

### The Clinical Flags

[If ClinVar variants were flagged: address them head-on but non-diagnostically — what "flagged" honestly means, why a single copy usually isn't alarming, and when it'd actually be worth a genetic counselor. Calm the reader without dismissing them. If none were found: one direct, reassuring sentence explaining why a clean clinical scan is genuinely meaningful — and what it does NOT rule out.]

### If You Do Three Things

[Exactly 3 specific action items, each tied to an actual finding above — not generic advice. Make them feel doable this week, not someday.]

---

*This narrative was generated from {first_name}'s genomic data and is educational, not diagnostic. The detailed findings, variant tables, and full evidence are in the sections below. Discuss anything that concerns you with a qualified clinician.*"""

    try:
        client = OpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL)
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content
        return content.strip() if content else ""
    except Exception as e:
        logger.error(f"OpenRouter/Claude narrative generation failed: {e}")
        return ""
