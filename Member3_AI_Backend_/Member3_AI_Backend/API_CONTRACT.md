# AI Customer Support Ticket API Contract

## Base URL
Local testing: `http://127.0.0.1:8000`

## Health Check
`GET /health`

Expected response:
```json
{
  "status": "healthy",
  "models_loaded": {
    "category_model": true,
    "priority_model": true
  },
  "model_version": "1.0"
}
```

## Prediction
`POST /predict`

Header:
`Content-Type: application/json`

Request:
```json
{
  "complaint": "My credit card was charged twice for one order."
}
```

Successful response:
```json
{
  "complaint": "My credit card was charged twice for one order.",
  "category": "billing_payment",
  "category_confidence": 0.3177,
  "priority": "high",
  "priority_confidence": 0.4453,
  "model_version": "1.0"
}
```

## Category Values
- `technical_support`
- `account_access`
- `billing_payment`
- `delivery_order`
- `general_enquiry`

## Priority Values
- `high`
- `medium`
- `low`

## Validation
Complaints shorter than three characters return HTTP `422`.

## Important
The original customer complaint should still be stored if the AI service is unavailable.
The backend should handle connection failures, timeouts, HTTP 422 and HTTP 500.
