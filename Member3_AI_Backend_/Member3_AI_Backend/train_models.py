"""Train and save the deployable category and priority models.

Only the explicit training and validation files are opened here.  The locked
test file is deliberately absent from this workflow.  The selected fitted model
objects are saved directly; there is no post-evaluation retraining step.
"""

from __future__ import annotations

import csv
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable

import joblib
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import FeatureUnion, Pipeline

from api.priority_policy import (
    PRIORITY_POLICY_CONFIDENCE,
    SEVERE_FINANCIAL_AMOUNT_THRESHOLD,
)


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
MODEL_DIR = ROOT / "models" / "final"
TRAIN_PATH = DATA_DIR / "customer_support_tickets_train.csv"
VALIDATION_PATH = DATA_DIR / "customer_support_tickets_validation.csv"
REQUIRED_SKLEARN_VERSION = "1.7.2"
MODEL_VERSION = "2.0.0"

CATEGORY_LABELS = [
    "account_access",
    "billing_payment",
    "delivery_order",
    "general_enquiry",
    "technical_support",
]
PRIORITY_LABELS = ["high", "low", "medium"]
CANDIDATE_CONFIGURATIONS = [
    {"name": "logistic_regression_C_0.1", "kind": "logistic", "value": 0.1},
    {"name": "logistic_regression_C_0.75", "kind": "logistic", "value": 0.75},
    {"name": "multinomial_nb_alpha_0.5", "kind": "multinomial_nb", "value": 0.5},
    {"name": "multinomial_nb_alpha_1.0", "kind": "multinomial_nb", "value": 1.0},
]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    required = {"complaint", "category", "priority", "group_id"}
    if not rows or not required.issubset(rows[0]):
        raise RuntimeError(f"Dataset is empty or missing columns: {path}")
    return rows


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_split_integrity(
    training_rows: list[dict[str, str]],
    validation_rows: list[dict[str, str]],
) -> None:
    training_groups = {row["group_id"] for row in training_rows}
    validation_groups = {row["group_id"] for row in validation_rows}
    if training_groups & validation_groups:
        raise RuntimeError("Training and validation group IDs overlap.")

    normalize = lambda value: " ".join(value.lower().split())
    training_texts = {normalize(row["complaint"]) for row in training_rows}
    validation_texts = {normalize(row["complaint"]) for row in validation_rows}
    if training_texts & validation_texts:
        raise RuntimeError("Training and validation complaint text overlaps.")


def make_pipeline(configuration: dict) -> Pipeline:
    features = FeatureUnion(
        [
            (
                "word",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    stop_words="english",
                    sublinear_tf=True,
                    strip_accents="unicode",
                    min_df=1,
                    max_df=0.995,
                ),
            ),
            (
                "character",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=(3, 5),
                    sublinear_tf=True,
                    strip_accents="unicode",
                    min_df=2,
                    max_features=18000,
                ),
            ),
        ]
    )
    if configuration["kind"] == "logistic":
        classifier = LogisticRegression(
            C=configuration["value"],
            max_iter=2000,
            penalty="l2",
            random_state=42,
            solver="lbfgs",
            tol=1e-4,
        )
    else:
        classifier = MultinomialNB(alpha=configuration["value"])
    return Pipeline([("features", features), ("classifier", classifier)])


def select_model(
    target: str,
    training_rows: list[dict[str, str]],
    validation_rows: list[dict[str, str]],
) -> tuple[Pipeline, dict]:
    training_texts = [row["complaint"] for row in training_rows]
    training_labels = [row[target] for row in training_rows]
    validation_texts = [row["complaint"] for row in validation_rows]
    validation_labels = [row[target] for row in validation_rows]

    candidates: list[tuple[tuple[float, float, int], Pipeline, dict]] = []
    for candidate_index, configuration in enumerate(CANDIDATE_CONFIGURATIONS):
        model = make_pipeline(configuration)
        model.fit(training_texts, training_labels)
        predicted = model.predict(validation_texts)
        metrics = {
            "name": configuration["name"],
            "kind": configuration["kind"],
            "value": configuration["value"],
            "accuracy": float(accuracy_score(validation_labels, predicted)),
            "macro_f1": float(
                f1_score(validation_labels, predicted, average="macro")
            ),
            "weighted_f1": float(
                f1_score(validation_labels, predicted, average="weighted")
            ),
        }
        # Prefer macro F1, then accuracy, then the earlier documented candidate
        # for a deterministic tie-break.
        ranking = (metrics["macro_f1"], metrics["accuracy"], -candidate_index)
        candidates.append((ranking, model, metrics))
        print(
            f"{target} {configuration['name']}: "
            f"validation_accuracy={metrics['accuracy']:.6f} "
            f"validation_macro_f1={metrics['macro_f1']:.6f}"
        )

    _, selected_model, selected_metrics = max(candidates, key=lambda item: item[0])
    return selected_model, {
        "selected_candidate": selected_metrics["name"],
        "selected_validation_metrics": selected_metrics,
        "candidate_validation_metrics": [item[2] for item in candidates],
    }


def label_counts(rows: Iterable[dict[str, str]], target: str) -> dict[str, int]:
    return dict(sorted(Counter(row[target] for row in rows).items()))


def atomic_joblib_dump(model: Pipeline, destination: Path) -> None:
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    joblib.dump(model, temporary)
    temporary.replace(destination)


def normalize_for_deterministic_serialization(model: Pipeline) -> None:
    """Remove process-specific cache state and order fitted vocabularies.

    scikit-learn caches ``id(stop_words)`` on word vectorizers. That memory
    address has no predictive meaning but otherwise changes the Joblib bytes on
    every process run. Removing it is safe: scikit-learn recreates the cache on
    first use. Sorting the fitted vocabulary dictionaries also makes their
    serialized order explicit without changing any assigned feature index.
    """

    features = model.named_steps["features"]
    for _, vectorizer in features.transformer_list:
        vectorizer.__dict__.pop("_stop_words_id", None)
        vectorizer.vocabulary_ = dict(sorted(vectorizer.vocabulary_.items()))


def main() -> None:
    if sklearn.__version__ != REQUIRED_SKLEARN_VERSION:
        raise RuntimeError(
            "Training must use the deployment scikit-learn version "
            f"{REQUIRED_SKLEARN_VERSION}; found {sklearn.__version__}."
        )

    training_rows = read_rows(TRAIN_PATH)
    validation_rows = read_rows(VALIDATION_PATH)
    assert_split_integrity(training_rows, validation_rows)

    category_model, category_selection = select_model(
        "category", training_rows, validation_rows
    )
    priority_model, priority_selection = select_model(
        "priority", training_rows, validation_rows
    )

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    normalize_for_deterministic_serialization(category_model)
    normalize_for_deterministic_serialization(priority_model)
    category_model_path = MODEL_DIR / "category_model.joblib"
    priority_model_path = MODEL_DIR / "priority_model.joblib"
    atomic_joblib_dump(category_model, category_model_path)
    atomic_joblib_dump(priority_model, priority_model_path)

    metadata = {
        "model_version": MODEL_VERSION,
        "dataset_type": "Curated synthetic academic prototype with fixed disjoint splits",
        "training_records": len(training_rows),
        "validation_records": len(validation_rows),
        "training_category_distribution": label_counts(training_rows, "category"),
        "training_priority_distribution": label_counts(training_rows, "priority"),
        "validation_category_distribution": label_counts(
            validation_rows, "category"
        ),
        "validation_priority_distribution": label_counts(
            validation_rows, "priority"
        ),
        "training_dataset_sha256": file_sha256(TRAIN_PATH),
        "validation_dataset_sha256": file_sha256(VALIDATION_PATH),
        "category_model_sha256": file_sha256(category_model_path),
        "priority_model_sha256": file_sha256(priority_model_path),
        "scikit_learn_version": sklearn.__version__,
        "joblib_version": joblib.__version__,
        "category_labels": CATEGORY_LABELS,
        "priority_labels": PRIORITY_LABELS,
        "category_model_selection": category_selection,
        "priority_model_selection": priority_selection,
        "priority_policy": {
            "severe_financial_amount_threshold": str(
                SEVERE_FINANCIAL_AMOUNT_THRESHOLD
            ),
            "override_confidence": PRIORITY_POLICY_CONFIDENCE,
            "confidence_semantics": (
                "Model probability for ordinary predictions; deterministic final "
                "routing confidence for a narrow safety-policy override."
            ),
        },
    }
    metadata_path = MODEL_DIR / "model_metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"Saved exact selected category model to {MODEL_DIR}")
    print(f"Saved exact selected priority model to {MODEL_DIR}")
    print(f"Saved metadata to {metadata_path}")


if __name__ == "__main__":
    main()
