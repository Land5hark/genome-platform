#!/usr/bin/env python3
"""
Basic integrity tests for two-tier report system.

Tests that Core and Deep Dive reports maintain proper separation
and don't create contradictions.
"""

import sys
from pathlib import Path

# Add scripts to path
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "Genetic Health" / "scripts"))

from generate_core_report import generate_core_report, assert_no_clinical_terms
from generate_deep_dive_report import generate_deep_dive_report, assert_proper_clinical_framing


def test_core_excludes_clinical_terms():
    """Core Report must NOT contain forbidden clinical terms."""
    sample_results = {
        'findings': [
            {'gene': 'CYP1A2', 'trait': 'Caffeine metabolism', 'genotype': 'AC', 'magnitude': 3,
             'summary': 'Slow caffeine metabolizer', 'category': 'Metabolism'}
        ],
        'pharmgkb_findings': [
            {'drug': 'Warfarin', 'gene': 'CYP2C9', 'level': '1A', 'phenotype': 'Normal', 'annotation': 'Standard dosing'}
        ]
    }

    core_md, core_html = generate_core_report(sample_results)

    # Should not contain clinical terms
    assert 'pathogenic' not in core_md.lower()
    assert 'pathogenic' not in core_html.lower()
    assert 'disease causing' not in core_md.lower()
    assert 'affected' not in core_md.lower()

    # Should pass assertion
    assert_no_clinical_terms(core_md)
    assert_no_clinical_terms(core_html)

    print("[PASS] Core Report excludes clinical terms")


def test_deep_dive_proper_framing():
    """Deep Dive must use non-diagnostic language."""
    sample_results = {
        'findings': [{'gene': 'CYP1A2', 'trait': 'Caffeine metabolism', 'category': 'Metabolism'}],
        'pharmgkb_findings': []
    }

    sample_disease = {
        'pathogenic': [
            {'gene': 'BRCA1', 'rsid': 'rs80357906', 'chromosome': '17', 'position': '43094692',
             'user_genotype': 'AG', 'traits': 'Breast cancer', 'gold_stars': 4, 'is_homozygous': False,
             'significance': 'pathogenic'}
        ],
        'likely_pathogenic': []
    }

    deep_dive_md, deep_dive_html = generate_deep_dive_report(sample_results, sample_disease)

    # Should include pathogenic findings
    assert 'BRCA1' in deep_dive_md
    assert 'pathogenic' in deep_dive_md.lower() or 'flagged' in deep_dive_md.lower()

    # Should NOT make definitive diagnostic claims
    assert 'you are diagnosed with breast cancer' not in deep_dive_md.lower()
    assert 'this confirms you have breast cancer' not in deep_dive_md.lower()

    print("[PASS] Deep Dive uses proper non-diagnostic framing")


def test_core_only_lifestyle_genetics():
    """Core Report should only include lifestyle findings."""
    sample_results = {
        'findings': [
            {'gene': 'CYP1A2', 'trait': 'Caffeine metabolism', 'genotype': 'AC', 'magnitude': 3,
             'summary': 'Slow caffeine metabolizer', 'category': 'Metabolism'},
            {'gene': 'BRCA1', 'trait': 'Breast cancer risk', 'genotype': 'AG', 'magnitude': 5,
             'summary': 'Disease risk', 'category': 'Disease Risk'},  # Should be excluded
        ],
        'pharmgkb_findings': []
    }

    core_md, core_html = generate_core_report(sample_results)

    # Should include lifestyle
    assert 'CYP1A2' in core_md
    assert 'Caffeine' in core_md

    # Should NOT include disease risk
    assert 'BRCA1' not in core_md
    assert 'Breast cancer' not in core_md

    print("[PASS] Core Report only includes lifestyle genetics")


def test_pharmgkb_level_filtering():
    """Core should only show Level 1A/1B PharmGKB, Deep Dive shows all."""
    sample_results = {
        'findings': [],
        'pharmgkb_findings': [
            {'drug': 'Warfarin', 'gene': 'CYP2C9', 'level': '1A', 'phenotype': 'Normal', 'annotation': 'Standard'},
            {'drug': 'Simvastatin', 'gene': 'SLCO1B1', 'level': '2A', 'phenotype': 'Reduced', 'annotation': 'Lower dose'},
        ]
    }

    core_md, _ = generate_core_report(sample_results)
    deep_dive_md, _ = generate_deep_dive_report(sample_results, {})

    # Core should have Level 1A only
    assert 'Warfarin' in core_md
    assert 'Simvastatin' not in core_md  # Level 2A excluded from quick card

    # Deep Dive should have all levels
    assert 'Warfarin' in deep_dive_md
    assert 'Simvastatin' in deep_dive_md

    print("[PASS] PharmGKB filtering works correctly")


def run_all_tests():
    """Run all integrity tests."""
    print("\n" + "="*60)
    print("Running Report Integrity Tests")
    print("="*60 + "\n")

    try:
        test_core_excludes_clinical_terms()
        test_deep_dive_proper_framing()
        test_core_only_lifestyle_genetics()
        test_pharmgkb_level_filtering()

        print("\n" + "="*60)
        print("[PASS] All tests passed!")
        print("="*60 + "\n")
        return 0

    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}\n")
        return 1
    except Exception as e:
        print(f"\n[FAIL] Error: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
