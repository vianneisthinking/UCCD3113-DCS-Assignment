# Exact AWS Account and PostgreSQL Coverage Verification

Perform these read-only checks before running any IaC. Do **not** click a final Create/Deploy button during verification.

## 1. Confirm account plan and expiry

1. Sign in to AWS as a billing-enabled identity.
2. Open the account menu → **Billing and Cost Management**.
3. On **Billing home**, record the displayed **Free plan/Paid plan**, credit balance, and Free Plan days/end date.
4. Open **Credits**. Record every credit's remaining amount, expiry, and applicable-service restrictions.
5. Open **Free Tier**. Search separately for `Lambda`, `API Gateway`, `S3`, `CloudFront`, `ECR`, `CloudWatch`, `RDS`, and `Aurora`; record current and forecast use.
6. Open **Bills** → current month → expand each service and Region. The expected starting value is zero.
7. Open **Cost Explorer** → month-to-date, group by **Service**, then by **Region**. Identify existing resources sharing allowances.
8. Open **Billing preferences** and enable Free Tier usage alerts and CloudWatch billing alerts; verify the recipient email.
9. Confirm the account is not in AWS Organizations. Joining Organizations upgrades a Free Plan account and expires its Free Tier credits.

## 2. Verify Aurora PostgreSQL Serverless Free Plan without creating it

1. Select **Asia Pacific (Singapore), `ap-southeast-1`** in the console.
2. Open **RDS** → **Databases**.
3. Look for **Create with express configuration in seconds**. Its presence is required for the proposed no-VPC design.
4. Choose **Create** only to open the review dialog; do not confirm creation.
5. Verify the dialog explicitly identifies **Aurora PostgreSQL Serverless** and **AWS Free Tier/Free Plan**.
6. Record the proposed capacity. It must remain at or below the Free Plan limit shown by AWS (currently up to 4 ACUs per cluster) and the project must remain below 1 GiB storage.
7. Confirm it uses **Aurora Standard**, one writer only, no manually added reader, no log exports, no Data API, and no paid add-ons.
8. Confirm the account/console presents the managed **internet access gateway** and **IAM authentication** express design. Do not select full configuration; full configuration is not the documented Aurora Free Plan path.
9. Capture the review screen and any estimated-cost/free-coverage text, then cancel/close the dialog.
10. Stop if the covered express option is not available in **Singapore, `ap-southeast-1`**; do not switch Regions for this deployment.

Free Plan express clusters are created outside a customer VPC, use an Aurora-managed internet access gateway, PostgreSQL wire protocol, IAM-only authentication, and IPv4. That is why the final application stack creates no VPC resources.

## 3. Verify conventional RDS PostgreSQL fallback

Use this only if Aurora express is unavailable.

1. In RDS choose **Create database** → **Standard create** → **PostgreSQL**.
2. Select the console's **Free tier** template if it is present for this account.
3. Check whether `db.t4g.micro` (or the exact instance class marked eligible) is identified as covered.
4. Select Single-AZ, the minimum eligible general-purpose storage, no autoscaling beyond the covered maximum, no read replica, no Performance Insights paid retention, no Enhanced Monitoring, no log exports, no RDS Proxy, and no Extended Support.
5. Expand **Estimated monthly costs**. Coverage must be stated explicitly or the estimate must be demonstrably credit-covered for the entire planned lifetime.
6. Take a screenshot, then cancel. Do not create the instance.

Conventional RDS needs customer VPC networking and is not included in the current no-VPC IaC. If it is selected, stop for a separate architecture review rather than modifying the stack during deployment.

## 4. Decision rule

- **Proceed to approval:** Aurora express Free Plan is visibly available, current credits/plan lifetime cover the assessment window, current bill is acceptable, and the Free Plan limits suit the project.
- **Escalate for review:** only conventional RDS is covered, because it changes networking.
- **Stop:** neither option is explicitly covered, the account is Paid with inadequate credits, or the expected assessment period exceeds the plan/credit expiry.

If console language is ambiguous, open **Support Center → Account and billing support** and request written confirmation for the exact account, Region, engine, express configuration, capacity, and planned duration. Billing support is available without buying a technical support plan.
