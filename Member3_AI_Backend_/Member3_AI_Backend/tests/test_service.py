"""Regression tests for the deployable FastAPI and direct Lambda interfaces."""

from __future__ import annotations

from decimal import Decimal
import unittest

from fastapi.testclient import TestClient

from api.main import app, category_model, model_metadata, priority_model
from api.priority_policy import parse_monetary_amounts
from lambda_handler import handler as lambda_handler


EXPECTED_RESPONSE_FIELDS = {
    "complaint",
    "category",
    "category_confidence",
    "priority",
    "priority_confidence",
    "model_version",
}


class ServiceRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def predict(self, complaint: str) -> dict:
        response = self.client.post("/predict", json={"complaint": complaint})
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(set(payload), EXPECTED_RESPONSE_FIELDS)
        return payload

    def test_models_load_with_expected_labels(self) -> None:
        self.assertIsNotNone(category_model)
        self.assertIsNotNone(priority_model)
        self.assertEqual(
            set(category_model.classes_),
            {
                "technical_support",
                "account_access",
                "billing_payment",
                "delivery_order",
                "general_enquiry",
            },
        )
        self.assertEqual(set(priority_model.classes_), {"high", "medium", "low"})
        self.assertEqual(model_metadata["scikit_learn_version"], "1.7.2")

    def test_health_is_backward_compatible(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "healthy")
        self.assertEqual(
            payload["models_loaded"],
            {"category_model": True, "priority_model": True},
        )
        self.assertEqual(payload["model_version"], "2.0.0")

    def test_predict_response_schema_is_exact(self) -> None:
        payload = self.predict("Where can I download an invoice copy?")
        self.assertEqual(set(payload), EXPECTED_RESPONSE_FIELDS)
        self.assertIsInstance(payload["category_confidence"], float)
        self.assertIsInstance(payload["priority_confidence"], float)

    def test_validation_errors(self) -> None:
        missing = self.client.post("/predict", json={})
        whitespace = self.client.post("/predict", json={"complaint": "   "})
        too_long = self.client.post("/predict", json={"complaint": "x" * 2001})
        self.assertEqual(missing.status_code, 422)
        self.assertEqual(whitespace.status_code, 422)
        self.assertEqual(too_long.status_code, 422)

    def test_usd_million_unauthorised_transfer_is_high(self) -> None:
        payload = self.predict(
            "Someone transferred $1 million from my account without permission."
        )
        self.assertEqual(payload["category"], "billing_payment")
        self.assertEqual(payload["priority"], "high")
        self.assertEqual(payload["priority_confidence"], 1.0)

    def test_rm_million_unauthorised_card_transaction_is_high(self) -> None:
        payload = self.predict(
            "There is an RM1,000,000 card transaction I did not make."
        )
        self.assertEqual(payload["category"], "billing_payment")
        self.assertEqual(payload["priority"], "high")
        self.assertEqual(payload["priority_confidence"], 1.0)

    def test_informational_finance_is_low(self) -> None:
        payload = self.predict("What payment methods do you accept?")
        self.assertEqual(payload["category"], "billing_payment")
        self.assertEqual(payload["priority"], "low")

    def test_delayed_refund_is_medium(self) -> None:
        payload = self.predict("My refund has not arrived yet.")
        self.assertEqual(payload["category"], "billing_payment")
        self.assertEqual(payload["priority"], "medium")

    def test_account_takeover_is_high(self) -> None:
        payload = self.predict(
            "Someone changed my password and recovery email and took over my account."
        )
        self.assertEqual(payload["category"], "account_access")
        self.assertEqual(payload["priority"], "high")

    def test_complete_outage_is_high(self) -> None:
        payload = self.predict(
            "The entire service is offline and all users are affected."
        )
        self.assertEqual(payload["category"], "technical_support")
        self.assertEqual(payload["priority"], "high")

    def test_delivery_complaint(self) -> None:
        payload = self.predict(
            "My parcel is five days late and tracking has not moved."
        )
        self.assertEqual(payload["category"], "delivery_order")
        self.assertEqual(payload["priority"], "medium")

    def test_general_enquiry(self) -> None:
        payload = self.predict("What time does the customer service centre open?")
        self.assertEqual(payload["category"], "general_enquiry")
        self.assertEqual(payload["priority"], "low")

    def test_typo_and_oov_wording(self) -> None:
        payload = self.predict("my paymnt was chargd twice pls chek it")
        self.assertEqual(payload["category"], "billing_payment")
        self.assertEqual(payload["priority"], "medium")

    def test_supported_monetary_formats(self) -> None:
        cases = {
            "$1,000": Decimal("1000"),
            "$1000000": Decimal("1000000"),
            "$1 million": Decimal("1000000"),
            "USD 50000": Decimal("50000"),
            "RM50,000": Decimal("50000"),
            "RM 1 million": Decimal("1000000"),
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(parse_monetary_amounts(text), [expected])

    def test_fastapi_lambda_prediction_parity(self) -> None:
        complaints = [
            "Someone transferred $1 million from my account without permission.",
            "What payment methods do you accept?",
            "The entire service is offline and all users are affected.",
            "My parcel is five days late and tracking has not moved.",
        ]
        for complaint in complaints:
            with self.subTest(complaint=complaint):
                http_payload = self.predict(complaint)
                direct_payload = lambda_handler(
                    {"complaint": complaint},
                    None,
                )
                self.assertEqual(direct_payload, http_payload)


if __name__ == "__main__":
    unittest.main()
