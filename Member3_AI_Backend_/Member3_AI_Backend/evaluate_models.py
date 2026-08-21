"""Evaluate the exact deployable models on the locked unseen test split only.

This script never calls fit and never performs model, threshold, or rule
selection. It also verifies that the current training/validation datasets match
the hashes recorded when the deployment artifacts were created.
"""

from __future__ import annotations

import csv
from hashlib import sha256
import json
from pathlib import Path

import joblib
import sklearn
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)

from api.priority_policy import apply_priority_policy


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
MODELS_DIR = ROOT / "models" / "final"
TEST_PATH = DATA_DIR / "customer_support_tickets_test.csv"
TRAIN_PATH = DATA_DIR / "customer_support_tickets_train.csv"
VALIDATION_PATH = DATA_DIR / "customer_support_tickets_validation.csv"
METADATA_PATH = MODELS_DIR / "model_metadata.json"

CATEGORY_LABELS = [
    "account_access",
    "billing_payment",
    "delivery_order",
    "general_enquiry",
    "technical_support",
]
PRIORITY_LABELS = ["high", "low", "medium"]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_provenance(
    test_rows: list[dict[str, str]],
    metadata: dict,
) -> None:
    if metadata.get("training_dataset_sha256") != file_sha256(TRAIN_PATH):
        raise RuntimeError("Training CSV does not match the saved model metadata.")
    if metadata.get("validation_dataset_sha256") != file_sha256(VALIDATION_PATH):
        raise RuntimeError("Validation CSV does not match the saved model metadata.")
    if metadata.get("category_model_sha256") != file_sha256(
        MODELS_DIR / "category_model.joblib"
    ):
        raise RuntimeError("Category model does not match the saved metadata.")
    if metadata.get("priority_model_sha256") != file_sha256(
        MODELS_DIR / "priority_model.joblib"
    ):
        raise RuntimeError("Priority model does not match the saved metadata.")
    if metadata.get("scikit_learn_version") != sklearn.__version__:
        raise RuntimeError(
            "Evaluation scikit-learn version differs from the training version: "
            f"trained={metadata.get('scikit_learn_version')} "
            f"current={sklearn.__version__}"
        )

    train_rows = read_rows(TRAIN_PATH)
    validation_rows = read_rows(VALIDATION_PATH)
    training_groups = {row["group_id"] for row in train_rows}
    validation_groups = {row["group_id"] for row in validation_rows}
    test_groups = {row["group_id"] for row in test_rows}
    if test_groups & (training_groups | validation_groups):
        raise RuntimeError("Locked test group IDs overlap another split.")

    normalize = lambda value: " ".join(value.lower().split())
    non_test_texts = {
        normalize(row["complaint"]) for row in train_rows + validation_rows
    }
    test_texts = {normalize(row["complaint"]) for row in test_rows}
    if non_test_texts & test_texts:
        raise RuntimeError("Locked test complaint text overlaps another split.")


def report(
    name: str,
    expected: list[str],
    predicted: list[str],
    labels: list[str],
) -> None:
    print(f"\n{name.upper()} — LOCKED TEST SET")
    print(f"accuracy={accuracy_score(expected, predicted):.6f}")
    print(
        classification_report(
            expected,
            predicted,
            labels=labels,
            digits=4,
            zero_division=0,
        )
    )
    print("confusion_matrix labels=", labels)
    print(confusion_matrix(expected, predicted, labels=labels))


def deployed_priority_predictions(model, texts: list[str]) -> list[str]:
    probabilities = model.predict_proba(texts)
    predictions: list[str] = []
    for text, row_probabilities in zip(texts, probabilities):
        index = int(row_probabilities.argmax())
        model_label = str(model.classes_[index])
        by_label = {
            str(label): float(probability)
            for label, probability in zip(model.classes_, row_probabilities)
        }
        predictions.append(
            apply_priority_policy(text, model_label, by_label).label
        )
    return predictions


def main() -> None:
    test_rows = read_rows(TEST_PATH)
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    verify_provenance(test_rows, metadata)

    texts = [row["complaint"] for row in test_rows]
    categories = [row["category"] for row in test_rows]
    priorities = [row["priority"] for row in test_rows]
    category_model = joblib.load(MODELS_DIR / "category_model.joblib")
    priority_model = joblib.load(MODELS_DIR / "priority_model.joblib")

    print(f"locked_test_records={len(test_rows)}")
    print(f"locked_test_sha256={file_sha256(TEST_PATH)}")
    print(f"model_version={metadata.get('model_version')}")
    print(f"scikit_learn_version={sklearn.__version__}")

    report(
        "category",
        categories,
        [str(value) for value in category_model.predict(texts)],
        CATEGORY_LABELS,
    )
    report(
        "priority",
        priorities,
        deployed_priority_predictions(priority_model, texts),
        PRIORITY_LABELS,
    )


if __name__ == "__main__":
    main()
