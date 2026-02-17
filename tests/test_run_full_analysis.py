import tempfile
import unittest
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / 'Genetic Health' / 'scripts'
sys.path.insert(0, str(SCRIPTS_DIR))

from run_full_analysis import load_genome, run_full_analysis  # noqa: E402


class RunFullAnalysisTests(unittest.TestCase):
    def test_load_genome_supports_23andme_and_ancestry(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)

            # 23andMe style: 4 columns with combined genotype
            g23 = td_path / 'genome_23.txt'
            g23.write_text('# comment\nrs1\t1\t100\tAG\nrs2\t1\t101\t--\n')

            rsid_map_23, pos_map_23 = load_genome(g23)
            self.assertIn('rs1', rsid_map_23)
            self.assertEqual('AG', rsid_map_23['rs1']['genotype'])
            self.assertNotIn('rs2', rsid_map_23)  # no-call filtered
            self.assertIn('1:100', pos_map_23)

            # Ancestry style: 5 columns with allele1/allele2
            ga = td_path / 'genome_ancestry.txt'
            ga.write_text('# comment\nrs3\t1\t200\tC\tT\n')

            rsid_map_a, pos_map_a = load_genome(ga)
            self.assertIn('rs3', rsid_map_a)
            self.assertEqual('CT', rsid_map_a['rs3']['genotype'])
            self.assertIn('1:200', pos_map_a)

    def test_run_full_analysis_writes_to_output_dir(self):
        genome_path = REPO_ROOT / 'AncestryDNA.txt'
        self.assertTrue(genome_path.exists(), 'Expected sample AncestryDNA.txt fixture')

        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / 'reports'
            result = run_full_analysis(genome_path=genome_path, subject_name='Test', output_dir=out_dir)

            self.assertEqual(out_dir, result['reports_dir'])
            self.assertTrue((out_dir / 'EXHAUSTIVE_GENETIC_REPORT.md').exists())
            self.assertTrue((out_dir / 'ACTIONABLE_HEALTH_PROTOCOL_V3.md').exists())
            self.assertTrue((out_dir / 'comprehensive_results.json').exists())


if __name__ == '__main__':
    unittest.main()
