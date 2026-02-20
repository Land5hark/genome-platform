# Two-Tier Product Implementation Guide

This document contains all the copy, mappings, code changes, and tests needed to implement the $39 Core + $79 Deep Dive product split.

---

## Part 1: Upsell Screen Copy

### Post-Purchase Upsell (After $39 Core Purchase)

**Headline:**
Curious About the Clinical Layer?

**Subheadline:**
Your Core Report covered wellness and medication response. Want to explore variants flagged in clinical databases?

**Body:**
The Deep Dive Clinical Context Report digs deeper into your genetic data, including:

- ✅ Variants flagged as pathogenic or likely pathogenic in ClinVar
- ✅ Clinical context: what these classifications mean and why confirmation is needed
- ✅ Full pharmacogenomics reference table
- ✅ Family planning and hereditary considerations
- ✅ Guidance on clinical-grade confirmatory testing

**Important:** This is still informational—not diagnostic. Any flagged variants require confirmation with clinical-grade testing before making health decisions.

**Button CTA:** Upgrade to Deep Dive — $79
**Secondary Link:** I'm good with my Core Report

**Trust Elements:**
- 🔒 One-time purchase, instant download
- 📄 Same data, deeper analysis
- 🩺 Built for sharing with your doctor

---

### Email Upgrade Offer

**Subject Line:** Your DNA story has another chapter (optional)

**Preview Text:** Explore clinical-grade database findings — entirely optional

**Email Body:**

Hi [Name],

Thanks for purchasing your DNA Decoder Core Report. I hope you're already finding actionable insights!

**Want to go deeper?**

Your Core Report focused on wellness genetics—the areas where you can take action today. But there's another layer available if you're curious:

**The Deep Dive Clinical Context Report** explores your data against clinical databases like ClinVar and PharmGKB. This optional report shows:

- Variants flagged as "pathogenic" or "likely pathogenic" (with clear explanations of what that means)
- Guidance on clinical confirmation testing
- Family planning and hereditary considerations
- Full pharmacogenomics reference table

**Who is this for?**

The Deep Dive is great if you:
- Have a family history of genetic conditions
- Are planning to have children
- Want a complete clinical reference to share with your doctor
- Are just curious and want the full picture

**Who doesn't need it?**

Most people find the Core Report gives them everything they need to take action on their wellness. The Deep Dive is entirely optional.

**A few important notes:**

✅ This is still informational—not diagnostic
✅ Any flagged variants need clinical-grade confirmation
✅ You're not missing anything actionable—the Core Report has that covered

[Upgrade to Deep Dive — $79]

Or just save this email and come back later if you change your mind.

Thanks,
The DNA Decoder Team

P.S. — Questions? Reply to this email anytime.

---

## Part 2: Data Mapping Table

This table defines which data goes into which report to prevent contradictions.

| Data Category | Source | $39 Core | $79 Deep Dive | Notes |
|---------------|--------|----------|---------------|-------|
| **Lifestyle Genetics Findings** | comprehensive_results.json → findings array | ✅ Include all | ✅ Include all | Caffeine, methylation, detox, metabolism, BP, sleep |
| **PharmGKB Annotations (Level 1A/1B)** | pharmgkb_findings → filtered by level | ✅ Quick card (top 5-10) | ✅ Full table | Core shows summary; Deep Dive shows all |
| **PharmGKB Annotations (Level 2+)** | pharmgkb_findings → Level 2A/2B/3 | ❌ Exclude | ✅ Include | Only in Deep Dive |
| **ClinVar Pathogenic Variants** | disease_risk.json → pathogenic | ❌ Exclude entirely | ✅ Include with context | Core MUST NOT mention these |
| **ClinVar Likely Pathogenic** | disease_risk.json → likely_pathogenic | ❌ Exclude entirely | ✅ Include with context | Core MUST NOT mention these |
| **ClinVar VUS (Uncertain)** | disease_risk.json → uncertain_significance | ❌ Exclude entirely | ✅ Include as VUS section | Deep Dive only |
| **ClinVar Benign Variants** | disease_risk.json → benign/likely_benign | ❌ Exclude | ❌ Exclude | Not useful in either report |
| **Action Protocol Supplements** | actionable_protocol.json → supplements | ✅ Include with "discuss with doctor" framing | ✅ Reference from Core | Behavioral actions in Core; supplements optional |
| **Action Protocol Behavioral** | actionable_protocol.json → behavioral | ✅ Include as 7-day experiments | ✅ Reference from Core | Core focus |
| **SNP Count & Stats** | comprehensive_results.json → metadata | ✅ Include | ✅ Include | Both reports show coverage stats |
| **Variant Footnotes** | findings array → rsids, genes | ✅ Appendix (lifestyle only) | ✅ Appendix (all clinical) | Different subsets |

---

## Part 3: Code Changes Required

### File: `Genetic Health/scripts/generate_core_report.py` (NEW FILE)

Create a new report generator that ONLY uses data approved for the $39 Core Report.

**Key functions:**

```python
def generate_core_report(results: dict, subject_name: str = None) -> tuple[str, str]:
    """
    Generate $39 Core Report (Markdown + HTML).

    EXCLUDES:
    - All ClinVar pathogenic/likely pathogenic/VUS variants
    - PharmGKB Level 2+ findings (only include 1A/1B)

    Returns:
        (markdown_content, html_content)
    """

    # Filter findings: lifestyle genetics only
    lifestyle_findings = filter_lifestyle_findings(results['findings'])

    # Filter pharma: Level 1A/1B only, top 5-10
    pharma_quick = filter_pharma_quick_card(results['pharmgkb_findings'])

    # Build action experiments (behavioral only)
    action_experiments = build_action_experiments(results['actionable_protocol'])

    # Build supplement section (with "discuss with doctor" framing)
    supplement_section = build_supplement_section(results['actionable_protocol'])

    # Render Markdown
    md_content = render_core_markdown(
        snps_analyzed=results['metadata']['snps_analyzed'],
        lifestyle_findings=lifestyle_findings,
        pharma_quick=pharma_quick,
        action_experiments=action_experiments,
        supplements=supplement_section,
        subject_name=subject_name
    )

    # Render HTML
    html_content = render_core_html(
        snps_analyzed=results['metadata']['snps_analyzed'],
        lifestyle_findings=lifestyle_findings,
        pharma_quick=pharma_quick,
        action_experiments=action_experiments,
        supplements=supplement_section,
        subject_name=subject_name
    )

    # CRITICAL: Assert no forbidden terms
    assert_no_clinical_terms(md_content)
    assert_no_clinical_terms(html_content)

    return md_content, html_content


def filter_lifestyle_findings(findings: list) -> list:
    """
    Filter findings to ONLY include lifestyle genetics categories.

    Allowed categories:
    - Caffeine metabolism
    - Methylation/MTHFR
    - Detoxification/antioxidants
    - Metabolism/weight/glucose
    - Blood pressure/cardiovascular tendencies
    - Sleep/circadian rhythm

    EXCLUDE any findings related to disease risk or clinical pathogenicity.
    """
    ALLOWED_CATEGORIES = [
        'caffeine', 'methylation', 'detox', 'metabolism',
        'cardiovascular', 'sleep', 'vitamin', 'nutrition'
    ]

    return [
        f for f in findings
        if any(cat in f.get('category', '').lower() for cat in ALLOWED_CATEGORIES)
    ]


def filter_pharma_quick_card(pharmgkb_findings: list) -> list:
    """
    Filter PharmGKB to Level 1A/1B only, top 5-10 by clinical importance.
    """
    level_1_findings = [
        f for f in pharmgkb_findings
        if f.get('level') in ['1A', '1B']
    ]

    # Sort by level (1A > 1B) and take top 10
    sorted_findings = sorted(
        level_1_findings,
        key=lambda x: (x['level'], x.get('drug', ''))
    )

    return sorted_findings[:10]


def assert_no_clinical_terms(content: str):
    """
    Assert that the Core Report does NOT contain forbidden clinical terms.

    This prevents contradictions with the Deep Dive report.
    """
    FORBIDDEN_TERMS = [
        'pathogenic', 'likely pathogenic', 'disease causing', 'affected',
        'clinvar', 'mutation', 'syndrome', 'disorder', 'carrier status',
        'homozygous affected', 'genetic disease', 'hereditary condition',
        'cancer risk', 'tumor', 'malignant', 'diagnosis'
    ]

    content_lower = content.lower()

    for term in FORBIDDEN_TERMS:
        if term in content_lower:
            raise ValueError(
                f"Core Report contains forbidden term: '{term}'. "
                f"This term must only appear in the Deep Dive report."
            )
```

---

### File: `Genetic Health/scripts/generate_deep_dive_report.py` (NEW FILE)

Create the Deep Dive report generator that CAN include clinical findings.

**Key functions:**

```python
def generate_deep_dive_report(results: dict, subject_name: str = None) -> tuple[str, str]:
    """
    Generate $79 Deep Dive Clinical Context Report (Markdown + HTML).

    INCLUDES:
    - All lifestyle genetics (same as Core)
    - Full PharmGKB table (all levels)
    - ClinVar pathogenic/likely pathogenic variants
    - VUS (variants of uncertain significance)
    - Clinical context and confirmatory testing guidance

    Returns:
        (markdown_content, html_content)
    """

    # Extract clinical findings
    pathogenic_variants = extract_pathogenic_variants(results['disease_risk'])
    vus_variants = extract_vus_variants(results['disease_risk'])

    # Full pharma table
    full_pharma_table = build_full_pharma_table(results['pharmgkb_findings'])

    # Render Markdown
    md_content = render_deep_dive_markdown(
        total_variants=results['metadata']['snps_analyzed'],
        pathogenic_variants=pathogenic_variants,
        vus_variants=vus_variants,
        full_pharma_table=full_pharma_table,
        subject_name=subject_name
    )

    # Render HTML
    html_content = render_deep_dive_html(
        total_variants=results['metadata']['snps_analyzed'],
        pathogenic_variants=pathogenic_variants,
        vus_variants=vus_variants,
        full_pharma_table=full_pharma_table,
        subject_name=subject_name
    )

    # Assert proper framing (no "you have", "affected", "diagnosed")
    assert_proper_clinical_framing(md_content)
    assert_proper_clinical_framing(html_content)

    return md_content, html_content


def extract_pathogenic_variants(disease_risk_data: dict) -> list:
    """
    Extract pathogenic and likely pathogenic variants from ClinVar data.

    Returns list of variants with:
    - gene
    - rsid
    - position
    - genotype
    - significance (pathogenic/likely pathogenic)
    - condition
    - evidence source
    """
    pathogenic = []

    for variant in disease_risk_data.get('variants', []):
        if variant.get('significance') in ['pathogenic', 'likely_pathogenic']:
            pathogenic.append({
                'gene': variant.get('gene'),
                'rsid': variant.get('rsid'),
                'position': variant.get('position'),
                'genotype': variant.get('genotype'),
                'significance': variant.get('significance'),
                'condition': variant.get('condition'),
                'evidence_source': variant.get('source', 'ClinVar'),
                'confidence': assess_confidence(variant)
            })

    return pathogenic


def assert_proper_clinical_framing(content: str):
    """
    Assert Deep Dive uses proper non-diagnostic language.

    FORBIDDEN phrases:
    - "you have [disease]"
    - "you are affected"
    - "you are diagnosed with"
    - "this means you have"

    REQUIRED framing:
    - "flagged for"
    - "warrants confirmation"
    - "potential association"
    - "clinical testing recommended"
    """
    FORBIDDEN_PHRASES = [
        r'you have \w+ (disease|syndrome|disorder|condition)',
        r'you are affected',
        r'you are diagnosed',
        r'this means you have',
        r'confirms that you',
    ]

    import re
    content_lower = content.lower()

    for pattern in FORBIDDEN_PHRASES:
        if re.search(pattern, content_lower):
            raise ValueError(
                f"Deep Dive report contains forbidden diagnostic language: {pattern}. "
                f"Use 'flagged', 'warrants confirmation', or 'potential association' instead."
            )
```

---

### File: `api/analyze.py` — Modifications

Update the `/api/success` endpoint to generate BOTH reports in the Deep Dive package:

```python
@app.route('/api/success', methods=['GET'])
def success():
    """
    Called after Stripe payment success.

    For $79 Deep Dive purchase:
    - Generate Core Report (MD + HTML)
    - Generate Deep Dive Report (MD + HTML)
    - Package all 4 files in ZIP
    """
    session_id = request.args.get('session_id')
    analysis_id = request.args.get('analysis_id')

    # Verify Stripe payment
    stripe_session = stripe.checkout.Session.retrieve(session_id)
    if stripe_session.payment_status != 'paid':
        return jsonify({"error": "Payment not confirmed"}), 400

    # Load analysis results
    session_path = SESSIONS_DIR / analysis_id
    results = json.loads((session_path / 'comprehensive_results.json').read_text())

    subject_name = stripe_session.metadata.get('subject_name', 'Subject')

    # Generate CORE report (included in Deep Dive package)
    from Genetic_Health.scripts.generate_core_report import generate_core_report
    core_md, core_html = generate_core_report(results, subject_name)

    # Generate DEEP DIVE report
    from Genetic_Health.scripts.generate_deep_dive_report import generate_deep_dive_report
    deep_dive_md, deep_dive_html = generate_deep_dive_report(results, subject_name)

    # Write files
    (session_path / 'DNA_DECODER_CORE_REPORT.md').write_text(core_md)
    (session_path / 'DNA_DECODER_CORE_REPORT.html').write_text(core_html)
    (session_path / 'DNA_DECODER_DEEP_DIVE_REPORT.md').write_text(deep_dive_md)
    (session_path / 'DNA_DECODER_DEEP_DIVE_REPORT.html').write_text(deep_dive_html)

    # Create ZIP with all 4 reports
    zip_path = session_path / 'DNA_DECODER_DEEP_DIVE_PACKAGE.zip'
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(session_path / 'DNA_DECODER_CORE_REPORT.md', 'DNA_DECODER_CORE_REPORT.md')
        zf.write(session_path / 'DNA_DECODER_CORE_REPORT.html', 'DNA_DECODER_CORE_REPORT.html')
        zf.write(session_path / 'DNA_DECODER_DEEP_DIVE_REPORT.md', 'DNA_DECODER_DEEP_DIVE_REPORT.md')
        zf.write(session_path / 'DNA_DECODER_DEEP_DIVE_REPORT.html', 'DNA_DECODER_DEEP_DIVE_REPORT.html')

    return send_file(zip_path, as_attachment=True, download_name='DNA_DECODER_DEEP_DIVE_PACKAGE.zip')
```

For the $39 Core purchase flow, create a new endpoint:

```python
@app.route('/api/checkout-core', methods=['POST'])
def checkout_core():
    """
    Create Stripe Checkout for $39 Core Report.
    """
    data = request.get_json()
    analysis_id = data.get('analysis_id')
    subject_name = data.get('subject_name', 'Subject')

    # Validate analysis_id exists
    if analysis_id not in SESSIONS:
        return jsonify({"error": "Invalid analysis_id"}), 400

    # Create Stripe Checkout Session
    checkout_session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'unit_amount': 3900,  # $39.00
                'product_data': {
                    'name': 'DNA Decoder Core Report',
                    'description': 'Lifestyle genetics + pharmacogenomics quick card'
                }
            },
            'quantity': 1
        }],
        mode='payment',
        success_url=f"{BASE_URL}/success-core?session_id={{CHECKOUT_SESSION_ID}}&analysis_id={analysis_id}",
        cancel_url=f"{BASE_URL}/",
        metadata={'analysis_id': analysis_id, 'subject_name': subject_name}
    )

    return jsonify({"checkout_url": checkout_session.url})


@app.route('/api/success-core', methods=['GET'])
def success_core():
    """
    Called after $39 Core Report purchase.

    Generate and deliver ONLY the Core Report (MD + HTML).
    """
    session_id = request.args.get('session_id')
    analysis_id = request.args.get('analysis_id')

    # Verify payment
    stripe_session = stripe.checkout.Session.retrieve(session_id)
    if stripe_session.payment_status != 'paid':
        return jsonify({"error": "Payment not confirmed"}), 400

    # Load results
    session_path = SESSIONS_DIR / analysis_id
    results = json.loads((session_path / 'comprehensive_results.json').read_text())

    subject_name = stripe_session.metadata.get('subject_name', 'Subject')

    # Generate Core Report
    from Genetic_Health.scripts.generate_core_report import generate_core_report
    core_md, core_html = generate_core_report(results, subject_name)

    # Write files
    (session_path / 'DNA_DECODER_CORE_REPORT.md').write_text(core_md)
    (session_path / 'DNA_DECODER_CORE_REPORT.html').write_text(core_html)

    # Create ZIP with Core Report only
    zip_path = session_path / 'DNA_DECODER_CORE_REPORT.zip'
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(session_path / 'DNA_DECODER_CORE_REPORT.md', 'DNA_DECODER_CORE_REPORT.md')
        zf.write(session_path / 'DNA_DECODER_CORE_REPORT.html', 'DNA_DECODER_CORE_REPORT.html')

    return send_file(zip_path, as_attachment=True, download_name='DNA_DECODER_CORE_REPORT.zip')
```

---

## Part 4: Unit Tests & Assertions

### File: `tests/test_report_integrity.py` (NEW FILE)

```python
import pytest
from Genetic_Health.scripts.generate_core_report import generate_core_report, assert_no_clinical_terms
from Genetic_Health.scripts.generate_deep_dive_report import generate_deep_dive_report, assert_proper_clinical_framing

# Sample test data
SAMPLE_RESULTS = {
    'metadata': {'snps_analyzed': 247},
    'findings': [
        {'gene': 'CYP1A2', 'category': 'caffeine', 'magnitude': 3},
        {'gene': 'MTHFR', 'category': 'methylation', 'magnitude': 4},
        {'gene': 'BRCA1', 'category': 'disease_risk', 'magnitude': 5}  # Should be excluded from Core
    ],
    'pharmgkb_findings': [
        {'drug': 'Warfarin', 'gene': 'CYP2C9', 'level': '1A'},
        {'drug': 'Clopidogrel', 'gene': 'CYP2C19', 'level': '1A'},
        {'drug': 'Simvastatin', 'gene': 'SLCO1B1', 'level': '2A'}  # Should be excluded from Core quick card
    ],
    'disease_risk': {
        'variants': [
            {'gene': 'BRCA1', 'rsid': 'rs80357906', 'significance': 'pathogenic', 'condition': 'Breast cancer'},
            {'gene': 'CFTR', 'rsid': 'rs113993960', 'significance': 'likely_pathogenic', 'condition': 'Cystic fibrosis'},
            {'gene': 'APOE', 'rsid': 'rs429358', 'significance': 'uncertain_significance', 'condition': 'Alzheimer\'s'}
        ]
    },
    'actionable_protocol': {
        'supplements': ['Methylfolate', 'B12'],
        'behavioral': ['Reduce caffeine after 2pm', 'Increase antioxidant-rich foods']
    }
}


def test_core_report_excludes_pathogenic_variants():
    """Core Report must NOT include any pathogenic/likely pathogenic variants."""
    core_md, core_html = generate_core_report(SAMPLE_RESULTS)

    # Assert no ClinVar pathogenic findings in Core
    assert 'BRCA1' not in core_md
    assert 'BRCA1' not in core_html
    assert 'pathogenic' not in core_md.lower()
    assert 'pathogenic' not in core_html.lower()


def test_core_report_excludes_forbidden_terms():
    """Core Report must NOT contain clinical disease language."""
    core_md, core_html = generate_core_report(SAMPLE_RESULTS)

    # Should pass the assertion
    assert_no_clinical_terms(core_md)
    assert_no_clinical_terms(core_html)


def test_core_report_includes_lifestyle_genetics():
    """Core Report MUST include lifestyle genetics findings."""
    core_md, core_html = generate_core_report(SAMPLE_RESULTS)

    assert 'CYP1A2' in core_md  # Caffeine metabolism
    assert 'MTHFR' in core_md   # Methylation
    assert 'caffeine' in core_md.lower()
    assert 'methylation' in core_md.lower()


def test_core_report_includes_pharma_quick_card():
    """Core Report must include Level 1A/1B PharmGKB findings only."""
    core_md, core_html = generate_core_report(SAMPLE_RESULTS)

    assert 'Warfarin' in core_md  # Level 1A
    assert 'Clopidogrel' in core_md  # Level 1A
    assert 'Simvastatin' not in core_md  # Level 2A - should be excluded from quick card


def test_deep_dive_includes_pathogenic_variants():
    """Deep Dive Report MUST include pathogenic/likely pathogenic findings."""
    deep_dive_md, deep_dive_html = generate_deep_dive_report(SAMPLE_RESULTS)

    assert 'BRCA1' in deep_dive_md
    assert 'CFTR' in deep_dive_md
    assert 'pathogenic' in deep_dive_md.lower()


def test_deep_dive_proper_framing():
    """Deep Dive must use non-diagnostic language."""
    deep_dive_md, deep_dive_html = generate_deep_dive_report(SAMPLE_RESULTS)

    # Should pass the assertion (no "you have X disease" language)
    assert_proper_clinical_framing(deep_dive_md)
    assert_proper_clinical_framing(deep_dive_html)

    # Should NOT say "you have breast cancer"
    assert 'you have breast cancer' not in deep_dive_md.lower()
    assert 'you are affected' not in deep_dive_md.lower()


def test_deep_dive_includes_vus():
    """Deep Dive should include VUS (variants of uncertain significance)."""
    deep_dive_md, deep_dive_html = generate_deep_dive_report(SAMPLE_RESULTS)

    assert 'APOE' in deep_dive_md  # VUS variant
    assert 'uncertain significance' in deep_dive_md.lower()


def test_deep_dive_includes_full_pharma_table():
    """Deep Dive must include ALL PharmGKB levels."""
    deep_dive_md, deep_dive_html = generate_deep_dive_report(SAMPLE_RESULTS)

    assert 'Warfarin' in deep_dive_md  # Level 1A
    assert 'Simvastatin' in deep_dive_md  # Level 2A (excluded from Core, included in Deep Dive)


def test_no_contradiction_between_reports():
    """
    Core Report must not claim 'no disease variants' if Deep Dive has pathogenic findings.

    This is the CRITICAL test to prevent the trust-destroying contradiction.
    """
    core_md, core_html = generate_core_report(SAMPLE_RESULTS)
    deep_dive_md, deep_dive_html = generate_deep_dive_report(SAMPLE_RESULTS)

    # If Deep Dive has pathogenic findings...
    if 'pathogenic' in deep_dive_md.lower():
        # ...then Core must NOT say "no disease causing variants"
        assert 'no disease causing variants' not in core_md.lower()
        assert 'no disease-causing variants' not in core_md.lower()
        assert 'no pathogenic variants' not in core_md.lower()

        # Core should instead say something like:
        assert 'deep dive' in core_md.lower() or 'clinical context' in core_md.lower()


def test_forbidden_terms_in_core():
    """Test that Core Report assertion correctly catches forbidden terms."""
    # Create a mock report with forbidden content
    mock_core_content = "Your analysis found a pathogenic variant in BRCA1. You are affected by this mutation."

    with pytest.raises(ValueError, match="forbidden term"):
        assert_no_clinical_terms(mock_core_content)


def test_forbidden_framing_in_deep_dive():
    """Test that Deep Dive assertion correctly catches diagnostic language."""
    # Create a mock Deep Dive with forbidden framing
    mock_deep_dive_content = "You have breast cancer based on this variant. You are diagnosed with this condition."

    with pytest.raises(ValueError, match="forbidden diagnostic language"):
        assert_proper_clinical_framing(mock_deep_dive_content)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

---

## Part 5: Release Checklist

Use this checklist before releasing the two-tier product:

### Pre-Release Testing

- [ ] Run `pytest tests/test_report_integrity.py` — all tests pass
- [ ] Generate sample Core Report — manually review for:
  - [ ] No pathogenic/likely pathogenic variants mentioned
  - [ ] No clinical disease language (affected, diagnosis, etc.)
  - [ ] Includes lifestyle genetics (caffeine, methylation, etc.)
  - [ ] Includes PharmGKB quick card (Level 1A/1B only)
  - [ ] Includes actionable experiments and supplements with "discuss with doctor" framing
  - [ ] Mentions Deep Dive as optional upgrade (not required)
- [ ] Generate sample Deep Dive Report — manually review for:
  - [ ] Includes pathogenic/likely pathogenic variants
  - [ ] Uses non-diagnostic framing ("flagged", "warrants confirmation", etc.)
  - [ ] Includes VUS section
  - [ ] Includes full PharmGKB table (all levels)
  - [ ] Includes confirmatory testing guidance
  - [ ] Includes family planning section
- [ ] Check contradiction: if Deep Dive has pathogenic findings, Core must not say "no disease variants"
- [ ] Test Stripe checkout flows:
  - [ ] $39 Core purchase → receives Core Report only (ZIP with MD + HTML)
  - [ ] $79 Deep Dive purchase → receives Deep Dive package (ZIP with 4 files: Core MD, Core HTML, Deep Dive MD, Deep Dive HTML)
- [ ] Test upsell flow:
  - [ ] After Core purchase, user sees upsell screen
  - [ ] User can decline and keep Core Report
  - [ ] User can upgrade to Deep Dive for additional $40 (or whatever pricing you set)

### Content Review

- [ ] Legal review of disclaimers in both reports
- [ ] Medical professional review of framing (confirm non-diagnostic language is clear)
- [ ] Reading level check (aim for 9th grade level in Core, 10th-11th in Deep Dive)
- [ ] Mobile responsiveness test (HTML versions)
- [ ] Print test (both MD and HTML should print cleanly)

### Data Integrity

- [ ] Verify all ClinVar pathogenic variants are excluded from Core Report generator
- [ ] Verify PharmGKB Level 2+ findings are excluded from Core quick card
- [ ] Verify Deep Dive includes all clinical findings with proper context
- [ ] Verify subject name is correctly populated in both reports
- [ ] Verify SNP counts and stats are accurate in both reports

### Stripe Configuration

- [ ] Create product in Stripe Dashboard: "DNA Decoder Core Report" at $39
- [ ] Create product in Stripe Dashboard: "DNA Decoder Deep Dive" at $79
- [ ] Test with Stripe test mode (card: 4242 4242 4242 4242)
- [ ] Configure success/cancel URLs correctly
- [ ] Add metadata to checkout sessions (analysis_id, subject_name)
- [ ] Switch to live mode for production launch

### Deployment

- [ ] Deploy updated `api/analyze.py` with new endpoints
- [ ] Deploy new report generators (`generate_core_report.py`, `generate_deep_dive_report.py`)
- [ ] Deploy updated frontend with:
  - [ ] Teaser screen after free analysis
  - [ ] $39 Core checkout flow
  - [ ] $79 Deep Dive checkout flow
  - [ ] Upsell screen after Core purchase
- [ ] Set environment variables:
  - [ ] `STRIPE_SECRET_KEY`
  - [ ] `BASE_URL`
  - [ ] `ANTHROPIC_API_KEY` (if using AI summary)
- [ ] Test end-to-end in production:
  - [ ] Upload genome file
  - [ ] See teaser insights
  - [ ] Purchase $39 Core
  - [ ] Receive Core Report
  - [ ] See upsell screen
  - [ ] Purchase $79 Deep Dive upgrade
  - [ ] Receive full Deep Dive package

### Launch

- [ ] Monitor first 10 purchases for any errors
- [ ] Check Stripe webhook logs
- [ ] Check server logs for report generation errors
- [ ] Collect initial customer feedback
- [ ] Track conversion rate: teaser → $39 Core
- [ ] Track upgrade rate: $39 Core → $79 Deep Dive

---

## Part 6: Future Enhancements

Post-launch improvements to consider:

1. **Add confidence scores to all findings** — use color coding (green/yellow/red)
2. **Email delivery option** — send reports via email in addition to download
3. **Report versioning** — allow users to regenerate reports as ClinVar updates
4. **Interactive HTML** — add collapsible sections, searchable tables, filtering
5. **PDF generation** — offer professional PDF in addition to HTML/MD
6. **Personalized language** — use subject name throughout reports
7. **Follow-up recommendations** — suggest specific genetic counselors or labs based on findings
8. **API access** — let users download raw JSON data
9. **Family sharing** — allow users to share redacted reports with relatives
10. **Health tracking integration** — connect with wearables to validate genetic predictions

---

**End of Implementation Guide**
