from pathlib import Path
import json
import sklearn

import joblib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


# ============================================================
# 1. Project file locations
# ============================================================

# main.py is stored inside the "api" folder.
API_DIR = Path(__file__).resolve().parent

# The parent of the "api" folder is AI_Ticket_System.
PROJECT_DIR = API_DIR.parent

# Final trained models are stored here.
FINAL_MODELS_DIR = PROJECT_DIR / "models" / "final"

CATEGORY_MODEL_PATH = (
    FINAL_MODELS_DIR / "category_model.joblib"
)

PRIORITY_MODEL_PATH = (
    FINAL_MODELS_DIR / "priority_model.joblib"
)

METADATA_PATH = (
    FINAL_MODELS_DIR / "model_metadata.json"
)


# ============================================================
# 2. Model-loading function
# ============================================================

def load_joblib_model(model_path: Path):
    """
    Load one trained Joblib model.

    A clear error is raised if the model file does not exist
    or cannot be loaded.
    """

    if not model_path.exists():
        raise RuntimeError(
            f"Required model file was not found: {model_path}"
        )

    try:
        model = joblib.load(model_path)

        # The supplied artifacts were serialized by scikit-learn 1.9.0, for
        # which no Linux CPython 3.12 wheel is available in the deployment
        # package index. Version 1.7 expects the legacy multi_class attribute
        # during predict_proba. Restoring only that removed state was verified
        # to produce byte-for-byte identical predictions and probabilities for
        # all 300 supplied records; the trained coefficients are unchanged.
        runtime_version = tuple(int(part) for part in sklearn.__version__.split(".")[:2])
        classifier = getattr(model, "named_steps", {}).get("classifier")
        if runtime_version < (1, 8) and classifier is not None and not hasattr(classifier, "multi_class"):
            classifier.multi_class = "deprecated"

        return model

    except Exception as error:
        raise RuntimeError(
            f"Unable to load model: {model_path}"
        ) from error


# Load both trained pipelines when the API starts.
category_model = load_joblib_model(
    CATEGORY_MODEL_PATH
)

priority_model = load_joblib_model(
    PRIORITY_MODEL_PATH
)


# ============================================================
# 3. Load optional model metadata
# ============================================================

model_metadata = {
    "model_version": "1.0",
    "training_records": 300,
    "dataset_type": "Synthetic academic prototype"
}

if METADATA_PATH.exists():
    try:
        with open(
            METADATA_PATH,
            "r",
            encoding="utf-8"
        ) as metadata_file:
            model_metadata = json.load(metadata_file)

    except (OSError, json.JSONDecodeError):
        # The API can still operate even if metadata
        # cannot be read.
        pass


# ============================================================
# 4. Request and response structures
# ============================================================

class TicketPredictionRequest(BaseModel):
    """
    Information received from the backend system.
    """

    complaint: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description=(
            "Customer complaint text to be classified."
        ),
        examples=[
            "My credit card was charged twice for one order."
        ]
    )


class TicketPredictionResponse(BaseModel):
    """
    Prediction information returned by the AI service.
    """

    complaint: str
    category: str
    category_confidence: float
    priority: str
    priority_confidence: float
    model_version: str


# ============================================================
# 5. Create the FastAPI application
# ============================================================

app = FastAPI(
    title="AI Customer Support Ticket API",
    description=(
        "REST API for customer-support ticket category "
        "and priority prediction."
    ),
    version="1.0.0"
)


# ============================================================
# 6. General API endpoints
# ============================================================

@app.get("/")
def read_root():
    """
    Return basic service information.
    """

    return {
        "service": "AI Customer Support Ticket API",
        "version": "1.0.0",
        "status": "running",
        "documentation": "/docs"
    }


@app.get("/health")
def health_check():
    """
    Confirm that the API and trained models are available.
    """

    return {
        "status": "healthy",
        "models_loaded": {
            "category_model": category_model is not None,
            "priority_model": priority_model is not None
        },
        "model_version": model_metadata.get(
            "model_version",
            "1.0"
        )
    }


# ============================================================
# 7. Ticket-prediction endpoint
# ============================================================

@app.post(
    "/predict",
    response_model=TicketPredictionResponse
)
def predict_ticket(
    request: TicketPredictionRequest
):
    """
    Predict the category and priority of one complaint.
    """

    # Remove unnecessary spaces from the beginning
    # and end of the complaint.
    complaint_text = request.complaint.strip()

    if len(complaint_text) < 3:
        raise HTTPException(
            status_code=422,
            detail=(
                "Complaint must contain at least "
                "three visible characters."
            )
        )

    try:
        # --------------------------------------------
        # Category prediction
        # --------------------------------------------

        predicted_category = (
            category_model.predict(
                [complaint_text]
            )[0]
        )

        category_probabilities = (
            category_model.predict_proba(
                [complaint_text]
            )[0]
        )

        category_confidence = float(
            category_probabilities.max()
        )

        # --------------------------------------------
        # Priority prediction
        # --------------------------------------------

        predicted_priority = (
            priority_model.predict(
                [complaint_text]
            )[0]
        )

        priority_probabilities = (
            priority_model.predict_proba(
                [complaint_text]
            )[0]
        )

        priority_confidence = float(
            priority_probabilities.max()
        )

        # --------------------------------------------
        # Return the prediction as JSON
        # --------------------------------------------

        return TicketPredictionResponse(
            complaint=complaint_text,
            category=str(predicted_category),
            category_confidence=round(
                category_confidence,
                4
            ),
            priority=str(predicted_priority),
            priority_confidence=round(
                priority_confidence,
                4
            ),
            model_version=str(
                model_metadata.get(
                    "model_version",
                    "1.0"
                )
            )
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "The AI service could not complete "
                "the prediction."
            )
        ) from error
