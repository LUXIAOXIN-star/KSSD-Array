#!/usr/bin/env python3

from pathlib import Path
import subprocess
import tempfile
import unittest

import sys

WORKFLOW = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKFLOW))

from s2_core import (  # noqa: E402
    bootstrap_paired_delta,
    compute_repeat_membership,
    exact_mcnemar_p,
    historical_compatible_correct,
    load_primary_assignments,
    load_truth_records,
    normalize_qname,
    paired_cells,
    strict_error_category,
    verify_fastq_truth_names,
)


class CorrectedS2CoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = WORKFLOW / "fixtures"
        cls.fixture_workspace = tempfile.TemporaryDirectory(
            prefix="kssd-s2-generated-fixtures-")
        cls.generated_root = Path(cls.fixture_workspace.name)
        generator = WORKFLOW.parents[2] / "tests/fixture_generators/generate_test_fixtures.sh"
        completed = subprocess.run(
            [str(generator), "--output-dir", str(cls.generated_root),
             "--seed", "42"],
            cwd=WORKFLOW.parents[2], text=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "fixture generation failed:\n" + completed.stdout + completed.stderr)
        cls.generated_fixture = (
            cls.generated_root /
            "reproducibility/minimap2/alignment_consistency_truth_origin/fixtures"
        )
        cls.truth = load_truth_records(
            cls.fixture / "truth.tsv", cls.fixture / "truth.aln", 10
        )

    @classmethod
    def tearDownClass(cls):
        cls.fixture_workspace.cleanup()

    def test_truth_coordinate_conversion_and_fastq_names(self):
        plus = self.truth["q_plus"]
        minus = self.truth["q_minus"]
        self.assertEqual((plus.start0, plus.end0, plus.sam_position1), (100, 110, 101))
        self.assertEqual((minus.start0, minus.end0, minus.sam_position1), (790, 800, 791))
        self.assertEqual(
            verify_fastq_truth_names(
                self.generated_fixture / "reads.fq", self.truth), 7)

    def test_query_name_normalization(self):
        self.assertEqual(normalize_qname("q_plus/1", self.truth), "q_plus")
        self.assertEqual(normalize_qname("missing/1", self.truth), "missing/1")

    def test_sam_flags_correctness_and_all_read_denominator(self):
        audit = load_primary_assignments(self.fixture / "assignments.sam", self.truth)
        self.assertEqual(audit.secondary_records, 1)
        self.assertEqual(audit.supplementary_records, 1)
        self.assertEqual(len(audit.assignments), 6)
        self.assertEqual(audit.primary_unmapped_seen, {"q_unmapped"})
        categories = {
            qname: strict_error_category(record, audit.assignments.get(qname), 5)
            for qname, record in self.truth.items()
        }
        self.assertEqual(categories["q_plus"], "correct")
        self.assertEqual(categories["q_minus"], "correct")
        self.assertEqual(categories["q_unmapped"], "unmapped_or_no_primary")
        self.assertEqual(categories["q_wrong_strand"], "wrong_strand")
        self.assertEqual(categories["q_wrong_ref"], "wrong_reference")
        self.assertEqual(categories["q_wrong_pos"], "wrong_position")
        self.assertEqual(sum(value == "correct" for value in categories.values()), 3)
        self.assertEqual(len(categories), 7)

    def test_historical_reverse_rule_is_not_art_genomic_conversion(self):
        audit = load_primary_assignments(self.fixture / "assignments.sam", self.truth)
        self.assertFalse(historical_compatible_correct(
            self.truth["q_minus"], audit.assignments["q_minus"], 5
        ))

    def test_repeat_overlap_uses_truth_interval(self):
        with tempfile.TemporaryDirectory() as temporary:
            members = compute_repeat_membership(
                self.truth, self.generated_fixture / "repeats.bed", Path(temporary)
            )
        self.assertEqual(members, {"q_plus", "q_minus"})

    def test_duplicate_primary_detection(self):
        audit = load_primary_assignments(
            self.fixture / "duplicate_primary.sam", self.truth
        )
        self.assertEqual(audit.duplicate_mapped_primary_queries, {"q_duplicate"})

    def test_paired_statistics_are_deterministic(self):
        original = [True, True, False, False, True]
        kssd = [True, False, True, False, True]
        cells = paired_cells(original, kssd)
        self.assertEqual(cells, (2, 1, 1, 1))
        first = bootstrap_paired_delta(cells, 10000, 42)
        second = bootstrap_paired_delta(cells, 10000, 42)
        self.assertEqual(first, second)
        self.assertEqual(exact_mcnemar_p(0, 0), 1.0)


if __name__ == "__main__":
    unittest.main()
