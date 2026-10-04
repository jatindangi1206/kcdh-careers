# AWS Deployment Approval Request — Free-First

Fill in the account, owners and domain before sending. This is a draft; no message has
been sent and no AWS resources have been provisioned.

## Message to send

**Subject: Approval for free-tier Ashoka Careers hosting — target $0/month**

I would like to host the Ashoka Careers jobs/internships page using free-tier/serverless
services. Visits and staff edits will be infrequent, so I propose avoiding a new always-on
server. Staff will keep their login and listing editor. Applicants follow form/website links
or apply by email; the app will not collect applications, CVs or uploaded files.

The proposed setup is static pages on private S3 behind CloudFront Free, with a small
on-demand Lambda API. We can retain the existing Upstash Free integration for postings,
staff names/emails/password hashes, sessions and login-failure counters. If external
storage is not approved, we can use DynamoDB provisioned free capacity instead; that
requires an additional storage-adapter change.

### Costs and resources

| Resource | Starting choice | Expected incremental monthly cost |
|---|---|---:|
| CloudFront | Flat-rate Free subscription | $0 |
| Lambda / Function URL | On-demand, initially 256 MB, small concurrency limit | $0 within available allowance |
| Storage | Upstash Free; alternatively DynamoDB Standard provisioned | $0 within available allowance |
| S3 | Small private assets and backup storage | Pennies possible for requests/versions |
| Domain / HTTPS | Supplied hostname, then an approved existing subdomain | Confirm DNS costs; no domain purchase |
| Logs / alerts | Short retention and existing monitoring | Confirm remaining allowances/charges |

**Target $0/month; expected $0–$1/month at low usage.** Please confirm remaining service
allowances, account eligibility and billing scope. This is a conditional estimate, not a hard
spending cap. Use a **$1 notification/review threshold** in the existing billing setup. There
should be no automatic paid upgrades. Any required paid service/plan will need specific
approval before provisioning.

This replaces the earlier $15 EC2 starting proposal. No new EC2 instance, EBS disk,
Elastic IP, NAT gateway, RDS instance or load balancer is requested. Limits were checked
on 4 October 2026 and should be refreshed at deployment:
[CloudFront](https://aws.amazon.com/cloudfront/pricing/),
[Lambda](https://aws.amazon.com/lambda/pricing/),
[Upstash](https://upstash.com/pricing/redis),
[DynamoDB](https://aws.amazon.com/dynamodb/pricing/) and
[CloudFront eligibility](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/flat-rate-pricing-plan.html).

### What I need confirmed

- Approved account/region, project tags/cost centre, remaining free allowances and whether
  CloudFront Free is selectable. My `freetier:GetFreeTierUsage` and Cost Explorer reads
  were denied, so I could not verify the actual available allowance or bill.
- Approval for one CloudFront Free distribution, small private S3 storage, one Lambda/URL
  and its limited execution role, plus public HTTPS delivery. You can provision them rather
  than grant account-wide administrator access.
- Whether Upstash Free is approved for the staff data above. Otherwise approve one small
  DynamoDB Standard provisioned table and confirm unused capacity/storage allowance.
  Do not select DynamoDB On-Demand by default.
- Production/staging hostname, DNS/certificate owner and charges. We can start with the
  supplied CloudFront hostname to avoid purchasing a domain or unrelated DNS zone.
- Named deployment role with MFA and approved release access. Staff use app accounts;
  they do not need IAM accounts, AWS console access, root credentials or SSH.
- Private backup/export location, retention, restore operator and log/data policy. Initially
  export after changes or at least weekly; automate if activity increases. Agree the
  acceptable data-loss window and verify a restore before launch.
- Application maintainer, cost/incident recipient and acceptance of cold starts, throttling
  at starting limits and no premium uptime SLA. Scale after measuring actual usage.
- Cutover window, staff editing freeze if changing stores, rollback owner and permission
  to retire old hosting only after this deployment and restore process are accepted.

The app needs a Lambda deployment adapter before this plan can deploy. The current
Vercel implementation is not an unchanged Lambda deployment. Details and checks are in
[AWS_MIGRATION.md](AWS_MIGRATION.md). Provisioning follows your approval and successful
implementation checks.

## Narrow permissions for the AWS administrator

Prefer manager-provisioned resources and a deployment role limited to this project. These
are capability groups to scope, not a wildcard IAM policy to paste.

| Identity | Typical actions | Scope |
|---|---|---|
| Manager/provisioner | CloudFront distribution/Free subscription and origin-access-control creation; Lambda `CreateFunction`, `CreateFunctionUrlConfig`, `AddPermission`; S3 bucket/policy/configuration; execution-role creation | New careers resources only; manager retains billing/subscription control |
| Deployment operator | Lambda `GetFunction`, `UpdateFunctionCode`, `UpdateFunctionConfiguration`, `PublishVersion`; approved CloudFront reads/updates/invalidations; S3 `PutObject`, `ListBucket` | Careers function/distribution and public-assets prefix; never publish private exports |
| Provisioner attaching IAM role | `iam:PassRole` | Only the approved execution role, passed to Lambda |
| Lambda runtime with Upstash | Minimal CloudWatch Logs writes | Own precreated log group; Upstash token in restricted configuration, never browser assets |
| Lambda runtime with DynamoDB | `dynamodb:GetItem`, `PutItem`, `UpdateItem`, `DeleteItem`, `Query`; additional reads only if implementation requires them | Single approved table/indexes; preserve conditional writes and expiry |
| DynamoDB provisioner, if chosen | `CreateTable`, `DescribeTable`, `UpdateTimeToLive`, necessary tags/settings | Standard provisioned table with small fixed capacity; no unapproved autoscaling |
| Backup/export operator | S3 `PutObject`, `GetObject`, prefix-restricted `ListBucket`; approved storage export reads | Private backup prefix, separate from frontend assets; no public access |
| DNS/certificate owner | Approved record changes and ACM certificate issuance/validation | Careers records only; CloudFront custom-domain certificate in `us-east-1` |
| Billing owner | Free Tier/Cost Explorer reads and agreed notifications/subscription control | Manager retains this; optional delegated read-only `freetier:GetFreeTierUsage` |

Protect both origins using CloudFront origin access control. Lambda resource permissions
should grant `lambda:InvokeFunctionUrl` and `lambda:InvokeFunction` to the approved
CloudFront distribution, rather than make the origin anonymously invokable. Application
login remains necessary for staff API operations. No runtime EC2/IAM administration or
access to all S3 buckets is needed.

Use blocked public S3 access, SSE-S3 and bounded backup retention. Price any policy-required
custom KMS key, paid secrets service, DynamoDB backups/PITR or extra alarms before approval.
Agree an export method that remains available when the free database reaches its limit.

## Approval record

| Decision | Approved value / owner |
|---|---|
| Account/region/tags and remaining service allowances | |
| CloudFront Free eligibility and supplied/custom hostname | |
| Upstash approved or DynamoDB chosen | |
| $0 target, notification threshold and billing recipient | |
| Deployment/execution roles and resource scope | |
| DNS/certificate owner and applicable costs | |
| Backup retention, restore operator and log/data policy | |
| Maintainer, incident contact and recovery expectations | |
| Approved release, cutover/rollback and retirement owner | |
| Manager approval and date | |
