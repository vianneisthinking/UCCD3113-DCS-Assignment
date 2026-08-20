# Presentation Architecture Notes

“We selected an on-demand serverless design because this is a very-low-traffic academic prototype. The customer and staff frontends are static assets behind CloudFront. API Gateway invokes the FastAPI backend through Mangum; the backend privately invokes a separate AI Lambda and persists results in PostgreSQL. This preserves real distributed service boundaries without paying for idle application servers.”

- Lambda rather than continuously running containers: compute is requested only when used; cold starts are an accepted demo limitation.
- Separate AI Lambda: IAM-protected service-to-service invocation demonstrates independent deployment/failure and keeps AI private.
- HTTP API rather than REST API: the app requires straightforward HTTP routing and token forwarding, not REST API-only features.
- PostgreSQL: preserves the relational SQLAlchemy design and Member 4 role, but deployment is conditional on explicit Free Plan coverage.
- Failure demonstration: stop/fail AI invocation, create a ticket, show `pending_classification`, restore AI, then reclassify.
- Academic AI statement: predictions run and supplied-data agreement is 100%, but that is resubstitution agreement, not defensible hold-out accuracy; training code/split are absent.
- Cost judgment: no NAT Gateway, load balancer, provisioned concurrency, custom domain, paid WAF, Multi-AZ database, or dedicated ML infrastructure.

Do not say AWS was deployed until screenshots and cloud tests exist. Current evidence is local Lambda-compatible runtime testing and package measurement.
