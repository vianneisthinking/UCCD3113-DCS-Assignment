"""Evaluate the supplied fitted models against the supplied synthetic dataset.

This is a reproducible artifact check, not a hold-out evaluation: the repository
does not contain the original training script or split indices, so data leakage
cannot be excluded. Results are written to stdout for documentation.
"""

import csv
from pathlib import Path

import joblib
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "data" / "customer_support_tickets_expanded.csv"
MODELS = ROOT / "models" / "final"


def load_dataset():
    with DATASET.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    return (
        [row["complaint"] for row in rows],
        [row["category"] for row in rows],
        [row["priority"] for row in rows],
    )


def evaluate(name, model, texts, expected):
    predicted = model.predict(texts)
    labels = list(model.classes_)
    print(f"\n{name.upper()}")
    print(f"accuracy={accuracy_score(expected, predicted):.6f}")
    print(classification_report(expected, predicted, labels=labels, digits=4, zero_division=0))
    print("confusion_matrix labels=", labels)
    print(confusion_matrix(expected, predicted, labels=labels))


def main():
    texts, categories, priorities = load_dataset()
    print(f"records={len(texts)}")
    evaluate("category", joblib.load(MODELS / "category_model.joblib"), texts, categories)
    evaluate("priority", joblib.load(MODELS / "priority_model.joblib"), texts, priorities)


if __name__ == "__main__":
    main()
