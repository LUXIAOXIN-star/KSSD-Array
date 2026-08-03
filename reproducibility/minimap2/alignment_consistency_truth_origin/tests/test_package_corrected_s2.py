#!/usr/bin/env python3
"""Tests for deterministic corrected-S2 provenance materialization."""

from pathlib import Path
import shutil
import tempfile
import unittest

import sys

WORKFLOW = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKFLOW))

from package_corrected_s2 import (  # noqa: E402
    FIXTURE_GENERATOR_SOURCES,
    PRIVATE_DEVELOPER_PATH,
    PROVENANCE_TEMPLATE,
    REVIEW_FILES,
    materialize_repository_state,
    package,
)


class CorrectedS2PackagingTest(unittest.TestCase):
    def make_workflow(self, root: Path) -> Path:
        repository = root / "repository"
        workflow = (
            repository /
            "reproducibility/minimap2/alignment_consistency_truth_origin"
        )
        target = workflow / PROVENANCE_TEMPLATE
        target.parent.mkdir(parents=True)
        shutil.copyfile(WORKFLOW / PROVENANCE_TEMPLATE, target)
        (workflow / "source.py").write_text("SOURCE = 'public'\n", encoding="utf-8")
        actual_repository = WORKFLOW.parents[2]
        for relative in FIXTURE_GENERATOR_SOURCES:
            dependency = repository / relative
            dependency.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(actual_repository / relative, dependency)
        return workflow

    @staticmethod
    def populate_review_outputs(output: Path) -> None:
        for name in REVIEW_FILES:
            if name in {"SOURCE_REPOSITORY_STATE.md", "source_sha256.tsv"}:
                continue
            (output / name).write_text("deterministic test: " + name + "\n",
                                       encoding="utf-8")

    def test_empty_output_materializes_template(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kssd-s2-package-empty-") as temporary:
            root = Path(temporary)
            workflow = self.make_workflow(root)
            output = root / "output"
            output.mkdir()
            target = materialize_repository_state(workflow, output)
            self.assertEqual(target.read_bytes(),
                             (workflow / PROVENANCE_TEMPLATE).read_bytes())

    def test_valid_existing_provenance_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kssd-s2-package-valid-") as temporary:
            root = Path(temporary)
            workflow = self.make_workflow(root)
            output = root / "output"
            output.mkdir()
            expected = (workflow / PROVENANCE_TEMPLATE).read_bytes()
            (output / "SOURCE_REPOSITORY_STATE.md").write_bytes(expected)
            self.assertEqual(materialize_repository_state(workflow, output).read_bytes(),
                             expected)

    def test_mismatched_existing_provenance_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kssd-s2-package-mismatch-") as temporary:
            root = Path(temporary)
            workflow = self.make_workflow(root)
            output = root / "output"
            output.mkdir()
            (output / "SOURCE_REPOSITORY_STATE.md").write_text(
                "# unrelated state\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "does not match"):
                materialize_repository_state(workflow, output)

    def test_missing_public_template_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kssd-s2-package-missing-") as temporary:
            root = Path(temporary)
            workflow = root / "workflow"
            workflow.mkdir()
            output = root / "output"
            output.mkdir()
            with self.assertRaisesRegex(FileNotFoundError, "missing public"):
                materialize_repository_state(workflow, output)

    def test_private_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kssd-s2-package-private-") as temporary:
            root = Path(temporary)
            workflow = self.make_workflow(root)
            output = root / "output"
            output.mkdir()
            (output / "SOURCE_REPOSITORY_STATE.md").write_text(
                "developer location: " + PRIVATE_DEVELOPER_PATH + "/work\n",
                encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "private path"):
                materialize_repository_state(workflow, output)

    def test_packaging_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kssd-s2-package-repeat-") as temporary:
            root = Path(temporary)
            workflow = self.make_workflow(root)
            output = root / "output"
            output.mkdir()
            self.populate_review_outputs(output)
            first_archive = package(workflow, output).read_bytes()
            first_inventory = (output / "output_sha256.tsv").read_bytes()
            source_inventory = (output / "source_sha256.tsv").read_text(
                encoding="utf-8")
            for relative in FIXTURE_GENERATOR_SOURCES:
                self.assertIn(str(relative), source_inventory)
            second_archive = package(workflow, output).read_bytes()
            second_inventory = (output / "output_sha256.tsv").read_bytes()
            self.assertEqual(first_archive, second_archive)
            self.assertEqual(first_inventory, second_inventory)


if __name__ == "__main__":
    unittest.main()
