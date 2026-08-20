# Backend-to-AI and Database Networking Decision

## Final pre-deployment choice

Both Lambda functions remain in the Lambda service-managed network, with no customer VPC attachment.

```text
API Gateway -> Backend Lambda -> AWS Lambda Invoke -> AI Lambda
                            |
                            +-> TLS PostgreSQL + IAM token
                                -> Aurora express internet access gateway
                                -> Aurora PostgreSQL
```

The backend execution role grants only `lambda:InvokeFunction` on the AI function and `rds-db:connect` for the selected Aurora resource/user. The AI has no URL, API route, or database permission.

Aurora Free Plan express configuration provides a managed internet access gateway, PostgreSQL wire-protocol access, and ephemeral IAM authentication. The backend generates a fresh RDS authentication token whenever SQLAlchemy opens a connection. `NullPool` prevents warm Lambda environments from retaining unnecessary idle connections. TLS is required.

## Rejected alternatives

- VPC Lambda plus NAT Gateway: prohibited continuous networking charge.
- VPC Lambda plus Lambda interface endpoint: paid hourly endpoint and unnecessary complexity.
- Dual-stack VPC plus IPv6 egress: workable in principle but unnecessary after express configuration; express database endpoints are IPv4-only.
- RDS Data API: removes VPC networking but requires Data API request usage and a Secrets Manager credential with separate charges, plus a larger persistence adaptation.
- Public AI URL/API route: unnecessary exposure and extra attack surface.

## Stop condition

If Aurora express Free Plan is unavailable, this networking design is not silently reused for conventional RDS. Conventional RDS requires a separate VPC architecture review before approval.
