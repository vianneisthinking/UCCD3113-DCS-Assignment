# Serverless IaC — Prepared, Not Deployed

This directory is a two-stage AWS SAM/CloudFormation design. No command below has been run against AWS.

## Why Aurora is a manual approval gate

Aurora Free Plan requires **Create with express configuration**. The current CloudFormation `AWS::RDS::DBCluster` schema does not expose the express `WithExpressConfiguration` operation or its internet-access-gateway networking flags. Creating a look-alike full-configuration cluster would lose the documented Free Plan path. Therefore the database is deliberately inspected and created only after the account check and explicit approval; all remaining resources are reproducible IaC.

## Intended approved sequence

1. Complete `docs/AWS_ACCOUNT_DATABASE_VERIFICATION.md`.
2. Validate templates: `cfn-lint bootstrap.yaml template.yaml`.
3. Deploy `bootstrap.yaml` only after approval; this creates the artifact bucket, AI ECR repository, and budget.
4. Build/push `Member3_AI_Backend_/Member3_AI_Backend/Dockerfile.lambda` to the immutable ECR tag.
5. Create the eligibility-confirmed Aurora express cluster through the reviewed console dialog. Record endpoint and cluster resource ID.
6. Run `prepare-parameters.ps1` to create standard SSM parameters, including one SecureString JWT secret.
7. Run `build-backend.ps1`, then package `template.yaml` using the bootstrap artifact bucket and deploy its reviewed change set.
8. Invoke the migration function once with `{"confirm":"upgrade-head"}`.
9. Run all application/failure tests and inspect Billing immediately.
10. Upload the frontends with `publish-frontends.ps1` and recheck Billing.

Use change sets and inspect every generated IAM/resource change before execution. Do not use `sam deploy --resolve-s3` or `--resolve-image-repos`, because those create additional unmanaged buckets/repositories beyond the inventory.
