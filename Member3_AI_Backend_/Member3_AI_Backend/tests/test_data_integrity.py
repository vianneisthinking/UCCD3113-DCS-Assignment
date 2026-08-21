"""Integrity tests for the immutable dataset boundaries and model provenance."""

from __future__ import annotations

import csv
from hashlib import sha256
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


def read_rows(name: str) -> list[dict[str, str]]:
    with (DATA_DIR / name).open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def file_sha256(path: Path) -> str:
    # Git may materialize text CSVs with CRLF on Windows even though the
    # committed/provenance bytes use LF. Hash canonical LF content so this
    # integrity assertion has identical meaning on every development OS.
    data = path.read_bytes()
    if path.suffix.lower() == ".csv":
        data = data.replace(b"\r\n", b"\n")
    return sha256(data).hexdigest()


class DatasetIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.train = read_rows("customer_support_tickets_train.csv")
        cls.validation = read_rows("customer_support_tickets_validation.csv")
        cls.test = read_rows("customer_support_tickets_test.csv")

    def test_expected_split_sizes(self) -> None:
        self.assertEqual(len(self.train), 600)
        self.assertEqual(len(self.validation), 90)
        self.assertEqual(len(self.test), 75)

    def test_group_ids_do_not_cross_splits(self) -> None:
        groups = [
            {row["group_id"] for row in rows}
            for rows in (self.train, self.validation, self.test)
        ]
        self.assertFalse(groups[0] & groups[1])
        self.assertFalse(groups[0] & groups[2])
        self.assertFalse(groups[1] & groups[2])

    def test_complaint_text_does_not_cross_splits(self) -> None:
        texts = [
            {" ".join(row["complaint"].lower().split()) for row in rows}
            for rows in (self.train, self.validation, self.test)
        ]
        self.assertFalse(texts[0] & texts[1])
        self.assertFalse(texts[0] & texts[2])
        self.assertFalse(texts[1] & texts[2])

    def test_model_metadata_matches_training_inputs(self) -> None:
        metadata = json.loads(
            (ROOT / "models" / "final" / "model_metadata.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            metadata["training_dataset_sha256"],
            file_sha256(DATA_DIR / "customer_support_tickets_train.csv"),
        )
        self.assertEqual(
            metadata["validation_dataset_sha256"],
            file_sha256(DATA_DIR / "customer_support_tickets_validation.csv"),
        )
        self.assertEqual(
            metadata["category_model_sha256"],
            file_sha256(ROOT / "models" / "final" / "category_model.joblib"),
        )
        self.assertEqual(
            metadata["priority_model_sha256"],
            file_sha256(ROOT / "models" / "final" / "priority_model.joblib"),
        )
        self.assertNotIn("test_dataset_sha256", metadata)

    def test_legacy_dataset_is_preserved_separately(self) -> None:
        legacy = DATA_DIR / "customer_support_tickets_expanded.csv"
        self.assertTrue(legacy.exists())
        self.assertNotEqual(legacy, DATA_DIR / "customer_support_tickets_test.csv")


if __name__ == "__main__":
    unittest.main()
