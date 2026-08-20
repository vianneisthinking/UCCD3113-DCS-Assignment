"""
Client for Member 3's AI classification service.

Every failure mode of that service — timeout, refused connection, 422, 500,
or a response that does not match the agreed contract — is collapsed into one
exception. The caller then has exactly one decision to make: classified, or
store it anyway.
"""

import json
import os

import httpx
from dotenv import load_dotenv

load_dotenv()


AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://127.0.0.1:8000").rstrip("/")
AI_TIMEOUT_SECONDS = float(os.getenv("AI_TIMEOUT_SECONDS", "5.0"))
AI_INVOCATION_MODE = os.getenv("AI_INVOCATION_MODE", "http").lower()
AI_LAMBDA_FUNCTION_NAME = os.getenv("AI_LAMBDA_FUNCTION_NAME", "")


class AIServiceUnavailable(Exception):
    """The classification could not be obtained. The ticket is still stored."""


def classify(complaint):
    """
    Return the classification for one complaint.

    Raises AIServiceUnavailable on any failure whatsoever.
    """

    try:
        if AI_INVOCATION_MODE == "lambda":
            if not AI_LAMBDA_FUNCTION_NAME:
                raise RuntimeError("AI_LAMBDA_FUNCTION_NAME is not configured")
            # boto3 is imported only in Lambda mode so local HTTP development
            # does not initialize AWS credential/metadata discovery.
            import boto3

            result = boto3.client("lambda").invoke(
                FunctionName=AI_LAMBDA_FUNCTION_NAME,
                InvocationType="RequestResponse",
                Payload=json.dumps({"complaint": complaint}).encode("utf-8"),
            )
            data = json.loads(result["Payload"].read())
            if result.get("FunctionError") or data.get("errorMessage"):
                raise RuntimeError(data.get("errorMessage", "AI Lambda failed"))
        else:
            response = httpx.post(
                f"{AI_SERVICE_URL}/predict",
                json={"complaint": complaint},
                timeout=AI_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            data = response.json()

    except Exception as error:
        raise AIServiceUnavailable(
            f"AI service did not answer: {error}"
        ) from error

    # The AI service is a separate system across a network, so its response is
    # untrusted input. A contract mismatch is a service failure, not a crash.
    try:
        return {
            "category": str(data["category"]),
            "category_confidence": float(data["category_confidence"]),
            "priority": str(data["priority"]),
            "priority_confidence": float(data["priority_confidence"]),
            "model_version": str(data.get("model_version", "unknown")),
        }

    except (KeyError, TypeError, ValueError) as error:
        raise AIServiceUnavailable(
            f"AI service returned an unexpected response: {error}"
        ) from error


def is_reachable():
    """Used by GET /health. Never raises."""

    try:
        if AI_INVOCATION_MODE == "lambda":
            if not AI_LAMBDA_FUNCTION_NAME:
                return False
            import boto3

            result = boto3.client("lambda").invoke(
                FunctionName=AI_LAMBDA_FUNCTION_NAME,
                InvocationType="RequestResponse",
                Payload=b'{"action":"health"}',
            )
            data = json.loads(result["Payload"].read())
            return not result.get("FunctionError") and data.get("status") == "healthy"
        response = httpx.get(f"{AI_SERVICE_URL}/health", timeout=2.0)
        return response.status_code == 200

    except Exception:
        return False
