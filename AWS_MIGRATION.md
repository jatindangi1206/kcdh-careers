# AWS Migration: Free-First Plan

For rare visits and occasional staff edits, use static hosting and a backend that runs only
when requested. **Target $0/month; expect $0–$1/month** if tiny storage/request/log charges
are not covered. This is a conditional estimate, not a guaranteed bill or spending cap.
The previous EC2 proposal is now an [optional paid fallback](AWS_EC2_RUNBOOK.md).

The public interface is static, but staff login, publishing and private accounts still need
a backend and durable storage. Static hosting alone would remove those working features.

## Recommended starting setup

Keep the app's existing **Upstash Free storage** and move hosting/API execution to AWS:

```text
Browser → CloudFront Free + HTTPS
          ├─ public/staff pages → private S3 assets bucket
          └─ /api/* → on-demand Lambda Function URL → Upstash Free
                                                      postings/accounts/sessions
```

This preserves the existing storage integration and account CLI. If the manager requires
all data to remain in AWS, use **DynamoDB Standard provisioned capacity** instead; that
requires a new storage adapter. Select one storage option rather than building both.

**Implementation status:** the repository supports local JSON and Vercel + Upstash today.
It does not yet have a Lambda event adapter or AWS serverless deployment configuration.
This is the revised cost/deployment plan, not a claim that the current app can deploy to
Lambda unchanged. No AWS resources were created. EC2 service/backup templates apply only
to the paid VM fallback.

## Costs and free allowances

Limits checked **4 October 2026**. Other projects may already consume shared allowances;
the manager must confirm eligibility, billing scope and available usage before approval.

| Component | Starting choice | Expected incremental monthly cost |
|---|---|---:|
| Frontend/CDN | CloudFront **flat-rate Free** subscription | $0 |
| CPU/RAM | On-demand Lambda, initially 256 MB per invocation | $0 within remaining free usage |
| HTTPS API endpoint | Lambda Function URL; no API Gateway | No separate endpoint fee |
| Existing storage | Upstash Free, upgrades and eviction disabled | $0 within plan limits |
| Assets/private backups | Small S3 buckets/prefixes | Pennies possible for requests/versions |
| DNS/HTTPS | Supplied CloudFront hostname or approved existing subdomain | Confirm DNS costs; no new domain purchase |
| Lambda logs | Minimal logs, short retention | Free allowance if available; otherwise usage charges |

CloudFront Free includes **1 million requests/month, 100 GB transfer and 5 GB S3 Standard
storage credits**. Its no-overage protection applies to that subscription, not to Lambda,
S3 requests, database operations or unrelated services.
[CloudFront pricing](https://aws.amazon.com/cloudfront/pricing/),
[plan eligibility and inclusions](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/flat-rate-pricing-plan.html).

Lambda includes **1 million requests and 400,000 GB-seconds/month**. CPU scales with memory;
there is no 24/7 CPU reservation. Start without provisioned concurrency, SnapStart or VPC/NAT
attachment. Accept cold starts, and measure login memory/latency at 256 MB; increase to
512 MB only if testing justifies it.
[Lambda pricing](https://aws.amazon.com/lambda/pricing/),
[Function URL costs](https://aws.amazon.com/about-aws/whats-new/2022/04/aws-lambda-function-urls-built-in-https-endpoints/).

Upstash Free includes **256 MB, 500,000 commands/month and 10 GB bandwidth/month**.
An API operation may use several Redis commands. Keep private backups and confirm the
selected integration plan. [Upstash pricing](https://upstash.com/pricing/redis).

The all-AWS alternative has a published DynamoDB allowance of **25 RCUs, 25 WCUs and
25 GB**, per Region/payer account, for Standard **provisioned** tables. Start with one small
table, e.g. 5 RCUs/5 WCUs, only if unused allowance is available. On-demand capacity does
not receive those provisioned units. Use separate posting records to avoid the 400 KB
per-item ceiling; preserve conditional writes, ownership checks and session expiry.
[DynamoDB pricing](https://aws.amazon.com/dynamodb/pricing/),
[item limits](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Constraints.html).

### Example at low traffic

Assume 1,000 visits/month, six asset requests and two API requests per visit, plus 100
staff/maintenance API requests: approximately 6,000 asset requests and 2,100 API requests.
At 256 MB and one second average execution, that is about **525 GB-seconds**. These are
planning assumptions, not measured traffic or latency; login/cold starts may take longer.

For data, 100 postings averaging 5 KB need about **0.5 MB**; 1,000 need about **5 MB**,
plus accounts and transient sessions. Documents/CVs remain external. No 16 GB app data
volume or large database allocation is needed. Watch actual commands, bandwidth, duration,
memory and errors after launch before scaling.

## Is this account eligible for $0?

**Possibly, but not verified.** The read-only `freetier:GetFreeTierUsage` request was denied,
as was the previous Cost Explorer check. Existing EC2 instances do not establish account
age, remaining credits, available recurring allowances or CloudFront subscription eligibility.
The manager should check Billing → Free Tier and the CloudFront plan selector.

Recurring service allowances differ from introductory credits. The new-customer Free
account plan ends after six months or exhausted credits; legacy EC2 introductory benefits
also expire. Creating another account is not the long-term hosting plan.
[AWS account plans](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html),
[legacy and recurring offers](https://repost.aws/knowledge-center/aws-free-tier-account-start-expire).

If CloudFront flat-rate Free is unavailable, price pay-as-you-go CloudFront against remaining
account allowances first; do not silently select a paid subscription. Start with the supplied
hostname. A new domain or unrelated DNS zone can introduce fixed charges.

## Approval and deployment sequence

Send [MANAGER_APPROVAL.md](MANAGER_APPROVAL.md). Target $0 with a **$1 notification/review
threshold**, using existing billing monitoring. Alerts are not hard caps. Any paid plan or
material recurring fee needs a revised, specific approval before provisioning.

1. **Confirm free choices.** Record account/region, unused allowances, approved storage,
   operator role, hostname and retention. Retain Upstash only with external-provider approval;
   its account owner must accept marketplace terms if provisioning is still pending.
2. **Implement and test Lambda support.** Adapt the existing HTTP handler to Function URL
   events/responses and package Linux-compatible Argon2 dependencies. Preserve validation,
   error handling, HTTPS cookies and owner restrictions. Keep sessions and failed-login
   counters in shared storage; Lambda memory and `/tmp` are not durable. For DynamoDB,
   implement/test the storage adapter and account/export commands before migrating data.
3. **Deploy assets and API.** Upload only `static/` assets to a private S3 origin; never
   publish `auth.json`, `.env*` or exports. Create one on-demand Lambda in Mumbai. Measure
   at 256 MB and use a small approved reserved-concurrency value, e.g. two. Reserved
   concurrency limits simultaneous execution, not monthly spend. No EC2/EBS/Elastic IP,
   RDS, load balancer or NAT gateway is requested.
4. **Configure CloudFront.** Use S3 for assets and `/api/*` for the Lambda origin. Map `/`
   to `index.html` and `/admin` to `admin.html`. Use managed policies supported by Free;
   disable API caching and forward required cookies/query strings. Protect both origins
   with origin access control, limiting Lambda invocation to the distribution. Lambda OAC
   requires a SHA-256 body header for POST/PUT; implement this in the frontend request
   helper and verify login and edits through CloudFront.
   [Lambda-origin OAC instructions](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-lambda.html).
5. **Preserve data/backups.** Verify the production Upstash environment/prefix; isolate
   previews. If changing stores, freeze staff/account changes and privately export/import
   postings and hashes, preserving IDs/ownership. Expire old sessions. Save a private export
   after changes or at least weekly while activity is rare; agree retention and test a restore.
   Start with an approved operator export process; automate when activity warrants it.
   The EC2 backup shell script cannot be used on Lambda.
6. **Verify and cut over.** Check public filters, expanded details, form/email/document links,
   job/internship publishing, login/logout, owner limits, archive/delete and persistence across
   Lambda replacements. Confirm private paths return 404, real quotas/costs and HTTPS;
   then update DNS. Retain old hosting for rollback. If stores differ, never allow both
   deployments to accept staff edits, and reconcile new writes before switching back.

Assign owners for account resets, dependency updates, backups, costs and incidents.
Free-tier limits and cold starts are acceptable starting compromises; security and data
preservation remain required.

## Other low-cost options

- **Existing approved university server:** potentially $0 incremental AWS resource cost
  if the manager confirms spare capacity and permits this app there. Do not assume a
  research/bastion server is available; shared hosting still needs backups and maintenance.
- **Vercel + Upstash:** requires the fewest code changes, but Vercel Hobby is restricted to
  non-commercial personal use. Do not promise that an official recruitment site qualifies;
  obtain confirmation or an approved institutional plan.
  [Vercel fair-use policy](https://vercel.com/docs/limits/fair-use-guidelines).
- **GitHub Pages/static hosting alone:** cannot run this Python staff backend. Keep the
  serverless API/storage if preserving staff login and publishing.
- **EC2/Lightsail trials:** temporary credits are useful for testing, not a permanent $0
  assumption. The [VM runbook](AWS_EC2_RUNBOOK.md) remains available if the manager chooses it.
