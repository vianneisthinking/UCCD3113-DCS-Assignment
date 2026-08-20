import json
import sys

import requests


# Local address of the AI prediction endpoint.
API_URL = "http://127.0.0.1:8000/predict"


def request_prediction(complaint: str) -> dict:
    """
    Send one customer complaint to the AI microservice
    and return the JSON prediction.
    """

    payload = {
        "complaint": complaint
    }

    try:
        response = requests.post(
            API_URL,
            json=payload,
            timeout=10
        )

        # Raise an error when the API returns
        # an unsuccessful HTTP status.
        response.raise_for_status()

        return response.json()

    except requests.exceptions.ConnectionError as error:
        raise RuntimeError(
            "Unable to connect to the AI API. "
            "Confirm that Uvicorn is running."
        ) from error

    except requests.exceptions.Timeout as error:
        raise RuntimeError(
            "The AI API did not respond within 10 seconds."
        ) from error

    except requests.exceptions.HTTPError as error:
        raise RuntimeError(
            f"The AI API returned HTTP {response.status_code}: "
            f"{response.text}"
        ) from error

    except requests.exceptions.RequestException as error:
        raise RuntimeError(
            "An unexpected API communication error occurred."
        ) from error


def main() -> None:
    """
    Test communication with the AI microservice.
    """

    test_complaints = [
        "My credit card was charged twice for one order.",
        "Someone changed my password and I cannot access my account.",
        "The mobile application crashes immediately after opening.",
        "My parcel is marked as delivered but it never arrived.",
        "What time does the customer service centre open?"
    ]

    print("=" * 70)
    print("AI MICROSERVICE CLIENT TEST")
    print("=" * 70)

    successful_requests = 0

    for number, complaint in enumerate(
        test_complaints,
        start=1
    ):
        print()
        print(f"Test {number}")
        print("-" * 70)
        print("Complaint:", complaint)

        try:
            prediction = request_prediction(complaint)

            print(
                "Category:",
                prediction["category"]
            )
            print(
                "Category confidence:",
                f'{prediction["category_confidence"] * 100:.2f}%'
            )
            print(
                "Priority:",
                prediction["priority"]
            )
            print(
                "Priority confidence:",
                f'{prediction["priority_confidence"] * 100:.2f}%'
            )
            print(
                "Model version:",
                prediction["model_version"]
            )

            successful_requests += 1

        except RuntimeError as error:
            print("Test failed:", error)

    print()
    print("=" * 70)
    print(
        f"Successful requests: "
        f"{successful_requests}/{len(test_complaints)}"
    )

    if successful_requests == len(test_complaints):
        print("All client-to-API communication tests passed.")
        sys.exit(0)

    print("One or more communication tests failed.")
    sys.exit(1)


if __name__ == "__main__":
    main()