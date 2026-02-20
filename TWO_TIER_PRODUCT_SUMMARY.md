# Two-Tier Product Redesign: Complete Summary

## Overview

This redesign splits the genome analysis product into two tiers:

1. **$39 Core Report** — Lifestyle genetics + pharmacogenomics quick card (impulse-friendly, empowering, actionable)
2. **$79 Deep Dive Report** — Clinical database findings + full pharma table + confirmatory testing guidance (optional, informational, requires clinical confirmation)

**Critical Problem Solved:** The original product created a trust-destroying contradiction where the Master Summary said "no disease causing variants" while the Disease Risk Report showed pathogenic items. This redesign eliminates that contradiction by separating wellness content from clinical content into two distinct products with different framing.

---

## File Locations

All templates and implementation guides are in:

```
Genetic Health/
  templates/
    core_report_template.md                    # $39 Core Report (Markdown)
    core_report_template.html                  # $39 Core Report (HTML)
    deep_dive_report_template.md               # $79 Deep Dive (Markdown)
    deep_dive_report_template.html             # $79 Deep Dive (HTML)
    upsell_and_implementation_guide.md         # Full implementation guide
```

---

## Product Comparison

| Feature | $39 Core Report | $79 Deep Dive Report |
|---------|----------------|----------------------|
| **Lifestyle genetics** (caffeine, methylation, detox, metabolism, BP, sleep) | ✅ Full coverage | ✅ Full coverage |
| **PharmGKB Level 1A/1B** (FDA-recognized drug interactions) | ✅ Quick card (top 5-10) | ✅ Full table |
| **PharmGKB Level 2+** (emerging drug evidence) | ❌ Not included | ✅ Full table |
| **ClinVar pathogenic variants** | ❌ Not included | ✅ Included with context |
| **ClinVar likely pathogenic variants** | ❌ Not included | ✅ Included with context |
| **VUS (uncertain significance)** | ❌ Not included | ✅ Included with explanation |
| **Actionable experiments** | ✅ 7-day behavioral tests | ✅ Referenced from Core |
| **Supplement suggestions** | ✅ With "discuss with doctor" framing | ✅ Referenced from Core |
| **Clinical confirmation guidance** | ❌ Not needed | ✅ Full section |
| **Family planning section** | ❌ Not included | ✅ Full section |
| **Contradictions with other products** | ✅ **Zero contradictions** | ✅ **Zero contradictions** |

---

## Key Design Principles

### 1. No Contradictions

**Rule:** If the Deep Dive includes pathogenic findings, the Core Report must NOT say "no disease causing variants."

**Solution:** The Core Report says:
> "This Core Report focuses on wellness genetics and medication response. If you're interested in exploring variants that may warrant confirmatory testing with a healthcare provider, that's available in the optional Deep Dive Clinical Context Report."

This framing:
- Doesn't claim "no disease variants"
- Positions Deep Dive as optional deeper layer
- Sets expectations clearly

### 2. Non-Diagnostic Language

**Core Report:**
- Educational only
- Focuses on actionable wellness
- No clinical disease labels
- No pathogenic/affected language

**Deep Dive Report:**
- Still educational, not diagnostic
- Uses "flagged", "warrants confirmation", "potential association"
- Never says "you have [disease]" or "you are affected"
- Always emphasizes need for clinical-grade confirmation

### 3. Trust-Building

**Core Report:**
- Empowering, clear, safe
- Immediate actionability
- No fear tactics
- Perfect for impulse purchase

**Deep Dive Report:**
- Calm, neutral tone
- Confidence levels prominently displayed
- Clear next steps for every finding
- Emphasizes uncertainty and limitations

### 4. Clear Upgrade Path

**Upsell Framing:**
- "Optional deeper layer" (not required)
- "Informational, not diagnostic" (clear expectations)
- "For those who want to explore clinical variants" (self-selecting audience)
- "Most people find the Core Report sufficient" (reduces pressure)

---

## Critical Implementation Rules

### Report Generation

**Core Report Generator (`generate_core_report.py`):**

```python
# MUST exclude:
- All ClinVar pathogenic/likely pathogenic variants
- All VUS (uncertain significance) variants
- PharmGKB Level 2+ findings (from quick card)
- Any clinical disease labels

# MUST include assertion:
assert_no_clinical_terms(content)
# Forbidden: pathogenic, affected, disease causing, diagnosis, etc.
```

**Deep Dive Generator (`generate_deep_dive_report.py`):**

```python
# CAN include:
- ClinVar pathogenic/likely pathogenic variants
- VUS variants (with explanation)
- Full PharmGKB table (all levels)

# MUST include assertion:
assert_proper_clinical_framing(content)
# Forbidden: "you have X", "you are affected", "you are diagnosed"
# Required: "flagged", "warrants confirmation", "potential association"
```

### Testing

**Run these tests before launch:**

```bash
pytest tests/test_report_integrity.py -v
```

**Critical tests:**
1. `test_core_report_excludes_pathogenic_variants` — Core has NO pathogenic content
2. `test_core_report_excludes_forbidden_terms` — Core has NO clinical disease language
3. `test_deep_dive_proper_framing` — Deep Dive uses non-diagnostic framing
4. `test_no_contradiction_between_reports` — No "no disease variants" claim if Deep Dive has pathogenic findings

---

## Upsell Strategy

### Where to Show Upsell

1. **Post-Core Purchase:**
   - Immediately after user downloads Core Report
   - Show upsell screen with Deep Dive benefits
   - Allow user to decline and keep Core only

2. **Email Follow-Up:**
   - Send upgrade email 24-48 hours after Core purchase
   - Subject: "Your DNA story has another chapter (optional)"
   - Emphasize optional nature

3. **In-Product CTA:**
   - Bottom of Core Report (both MD and HTML)
   - Subtle, not pushy
   - "Need More?" section

### Upsell Copy Formula

**Headline:** Acknowledge their current purchase
**Subheadline:** Position Deep Dive as optional deeper layer
**Body:** List what's included (clinical findings, confirmation guidance, family planning)
**Reassurance:** "This is still informational—not diagnostic"
**CTA:** Clear pricing and instant access
**Exit:** "I'm good with my Core Report" option

---

## Pricing Strategy

**Current Plan:**
- $39 for Core Report
- $79 for Deep Dive (includes Core + clinical layer)

**Alternative Models:**

1. **Tiered Pricing:**
   - $39 Core only
   - $79 Deep Dive only (without Core)
   - $99 Complete Bundle (both reports)

2. **Upgrade Pricing:**
   - $39 Core only
   - +$40 to upgrade to Deep Dive (total $79)
   - Incentivizes initial purchase

3. **Subscription Model:**
   - $39 one-time for Core
   - $19/year for annual Deep Dive updates (as ClinVar evolves)

**Recommendation:** Start with $39 Core + $79 Deep Dive (includes Core). Track conversion rates and adjust.

---

## Launch Checklist (Quick Reference)

### Pre-Launch
- [ ] Deploy new report generators
- [ ] Deploy new API endpoints (`/api/checkout-core`, `/api/success-core`)
- [ ] Update frontend with teaser screen and checkout flows
- [ ] Configure Stripe products ($39 Core, $79 Deep Dive)
- [ ] Run all unit tests
- [ ] Manual review of sample reports

### Day 1
- [ ] Monitor first 10 purchases
- [ ] Check Stripe logs for payment issues
- [ ] Check server logs for report generation errors
- [ ] Verify ZIP downloads work correctly

### Week 1
- [ ] Track conversion rate: teaser → $39 Core
- [ ] Track upgrade rate: $39 Core → $79 Deep Dive
- [ ] Collect customer feedback
- [ ] Review support tickets for confusion points

### Month 1
- [ ] Analyze which findings drive upgrades
- [ ] Test A/B variations of upsell copy
- [ ] Consider adding confidence scores/color coding
- [ ] Plan for report versioning (ClinVar updates)

---

## Messaging Guidelines

### What to Say

**Core Report:**
- "Your genes suggest..."
- "This pattern may mean..."
- "Try this experiment..."
- "Discuss with your doctor..."
- "These are tendencies, not certainties"

**Deep Dive Report:**
- "This variant has been flagged in ClinVar"
- "Clinical confirmation is needed"
- "This warrants discussion with a genetic counselor"
- "Potential association with..."
- "May indicate increased risk, pending confirmation"

### What NOT to Say

**Core Report:**
- ❌ "You have no disease-causing variants"
- ❌ "Your genes are clean"
- ❌ "No mutations detected"

**Deep Dive Report:**
- ❌ "You have [disease]"
- ❌ "You are affected by this condition"
- ❌ "This confirms a diagnosis"
- ❌ "You will develop [disease]"

---

## Customer Segments

### Who Buys $39 Core Only

- Health-conscious wellness seekers
- Curious about nutrition/fitness optimization
- Want actionable lifestyle tweaks
- Not particularly concerned about family history
- Prefer simple, clear guidance

**Marketing Angle:** "Unlock your wellness blueprint"

### Who Upgrades to $79 Deep Dive

- Family history of genetic conditions
- Planning to have children (carrier screening)
- Recently diagnosed with something and looking for answers
- Taking multiple medications (pharma interactions)
- Want comprehensive reference for doctors
- Science-curious individuals who want the full picture

**Marketing Angle:** "The optional clinical layer for comprehensive insight"

---

## Technical Architecture

### Data Flow

1. **Free Analysis:**
   - User uploads genome file
   - Backend runs full analysis (all databases)
   - Returns teaser insights (3-5 top findings)
   - Stores full results in `.sessions/{analysis_id}/`

2. **$39 Core Purchase:**
   - Stripe Checkout → `/api/checkout-core`
   - Payment success → `/api/success-core`
   - Generate Core Report (MD + HTML)
   - Return ZIP with 2 files
   - Show upsell screen

3. **$79 Deep Dive Purchase:**
   - Stripe Checkout → `/api/checkout` (existing endpoint)
   - Payment success → `/api/success`
   - Generate Core Report + Deep Dive Report (4 files total)
   - Return ZIP with all 4 files

### File Storage

```
.sessions/
  {analysis_id}/
    comprehensive_results.json          # Full analysis data
    DNA_DECODER_CORE_REPORT.md          # Generated on Core purchase
    DNA_DECODER_CORE_REPORT.html        # Generated on Core purchase
    DNA_DECODER_DEEP_DIVE_REPORT.md     # Generated on Deep Dive purchase
    DNA_DECODER_DEEP_DIVE_REPORT.html   # Generated on Deep Dive purchase
    DNA_DECODER_CORE_REPORT.zip         # For $39 purchasers
    DNA_DECODER_DEEP_DIVE_PACKAGE.zip   # For $79 purchasers
```

---

## Success Metrics

### Primary KPIs

1. **Conversion Rate: Teaser → $39 Core**
   - Target: 5-15% (impulse purchase)
   - Optimize: Teaser insights, pricing, messaging

2. **Upgrade Rate: $39 Core → $79 Deep Dive**
   - Target: 20-40% (optional upsell)
   - Optimize: Upsell copy, timing, Deep Dive value prop

3. **Customer Satisfaction**
   - Target: 4.5+ stars, <5% refund rate
   - Optimize: Report clarity, actionability, trust

### Secondary KPIs

- Average revenue per user (ARPU)
- Time from teaser to Core purchase
- Time from Core to Deep Dive upgrade
- Support ticket volume (indicates confusion)
- Referral rate (word-of-mouth)

---

## Risk Mitigation

### Legal/Compliance

- **Disclaimers in both reports:** "Educational, not diagnostic"
- **No medical advice:** Always say "discuss with your doctor"
- **Privacy:** Don't store raw genetic data long-term
- **Accuracy:** Emphasize limitations of raw data

### Customer Trust

- **No contradictions:** Core and Deep Dive must align
- **No fear tactics:** Calm, neutral tone throughout
- **Clear expectations:** "Informational only, confirmation needed"
- **Easy refunds:** Offer 30-day money-back guarantee

### Technical

- **Data security:** Encrypt sessions, delete old data
- **Report accuracy:** Assertions catch forbidden content
- **Payment reliability:** Stripe handles edge cases
- **Scalability:** Reports generate in <30 seconds

---

## Next Steps

1. **Immediate:** Review templates and implementation guide
2. **Week 1:** Build report generators with assertions
3. **Week 2:** Update API endpoints and Stripe integration
4. **Week 3:** Build frontend teaser and checkout flows
5. **Week 4:** Testing (unit tests + manual review)
6. **Week 5:** Soft launch with small audience
7. **Week 6:** Full launch + monitoring

---

**Questions? Concerns? Adjustments needed?**

All templates are in `Genetic Health/templates/`. Full implementation details are in `upsell_and_implementation_guide.md`.
