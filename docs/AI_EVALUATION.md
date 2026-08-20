# AI Model Evaluation

## Dataset

The supplied `customer_support_tickets_expanded.csv` contains 300 synthetic academic support complaints. The only model input is the `complaint` text. It has five balanced category labels (60 records each) and three balanced priority labels (100 records each).

Category labels: `account_access`, `billing_payment`, `delivery_order`, `general_enquiry`, and `technical_support`.

Priority labels: `high`, `low`, and `medium`.

## Supplied Models and Preprocessing

Both Joblib artifacts are scikit-learn `Pipeline` objects containing:

1. `TfidfVectorizer(ngram_range=(1, 2), stop_words="english", sublinear_tf=True)`
2. `LogisticRegression(max_iter=1000, random_state=42)`

The artifacts therefore preserve inference preprocessing and classifier configuration. The repository does not contain the training script, dataset generation script, train/test indices, cross-validation results, notebook, or original evaluation output.

## Reproducible Artifact Check

`evaluate_models.py` loads the CSV and fitted artifacts, predicts all 300 supplied rows, and calculates scikit-learn accuracy, precision, recall, F1, and confusion matrices.

Observed results on 20 August 2026:

| Target | Accuracy | Macro precision | Macro recall | Macro F1 |
|---|---:|---:|---:|---:|
| Category | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| Priority | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

All category classes had 60/60 correct predictions. All priority classes had 100/100 correct predictions.

## Critical Interpretation

These are supplied-dataset agreement (resubstitution) results, not a trustworthy estimate of unseen-data performance. The fitted models may have been trained on the same 300 rows, and the repository provides no split indices with which to prove otherwise. The perfect scores must not be described as test accuracy in the report.

The API smoke examples also showed modest confidence: category confidence ranged from approximately 31.77% to 70.90%, and priority confidence from approximately 35.84% to 44.97%. This reinforces that the prototype should not be claimed as production-quality AI.

Member 3 still needs to provide the original training code or notebook and a fixed, seeded train/test split for a valid hold-out evaluation. A future reproducible workflow should use stratified splitting, fit TF-IDF only on training data, and report held-out per-class and macro/weighted metrics.

## Runtime Measurements

| Measurement | Observed |
|---|---:|
| Category model file | 57,652 bytes |
| Priority model file | 44,180 bytes |
| Combined artifacts | 101,832 bytes |
| AI process working set after loading | 137.4 MB |
| AI process private memory reported by Windows | 1,074 MB reserved/committed |
| 30-call median inference HTTP latency | 15.87 ms |
| 30-call measured p95 | 27.35 ms |

The working set is the more representative measure of resident physical memory. Container measurement is still required because Linux runtime behavior and image libraries differ.

## Limitations

- Synthetic, small, and likely template-generated dataset.
- No original training workflow or independent test set.
- No evidence of robustness to spelling, mixed-language complaints, ambiguous tickets, or distribution drift.
- Confidence values are not calibrated.
- Evaluation covers classification behavior, not business routing correctness.
