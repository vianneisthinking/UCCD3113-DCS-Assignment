"""Private direct-invocation AWS Lambda entry point for AI inference."""

from api.main import TicketPredictionRequest, model_metadata, predict_ticket


def handler(event, context):
    if event.get("action") == "health":
        return {
            "status": "healthy",
            "models_loaded": True,
            "model_version": str(model_metadata.get("model_version", "1.0")),
        }

    request = TicketPredictionRequest.model_validate(event)
    return predict_ticket(request).model_dump()
