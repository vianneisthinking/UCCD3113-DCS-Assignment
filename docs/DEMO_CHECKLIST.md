# 3–5 Minute Demonstration Checklist

## Primary Demonstration

1. Open the hosted customer URL and confirm the CloudFront HTTPS address.
2. Log in or register a demonstration customer.
3. Submit: “I was charged twice for my monthly subscription.”
4. Show the created ticket. Do not announce an expected category/priority before the live response; the tested run produced `billing_payment` and `medium`.
5. Point out the AI category, priority, department, and open status.
6. Open `/staff/index.html`, sign in using a prepared staff account, and find the same numeric ticket ID.
7. Use search and one status/priority filter.
8. Open the ticket and change Open → In Progress.
9. Return to the customer portal, refresh, and show In Progress.
10. Briefly show the architecture diagram and AWS resource overview/CloudWatch logs.

Never show passwords, JWTs, database endpoints, account IDs, access keys, or SSM SecureString values.

## AI Failure Contingency

If AI is unavailable, demonstrate that submission still succeeds as `pending_classification`. Explain graceful degradation, restore AI, use “Retry AI classification” in the staff drawer, then show the populated category/priority.

## AWS Failure Contingency

Use the recorded local API results, real screenshots collected after deployment, architecture diagram, and a permitted local demonstration. Do not present proposed resources or unexecuted tests as successful cloud evidence.
