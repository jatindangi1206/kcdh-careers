# AWS Deployment Approval Request

Copy/adapt the message below for the AWS manager. Fill in the proposed domain, owners and
cost centre before sending. This file is a draft; no message or deployment has been sent.

## Message to send

**Subject: Approval for Ashoka Careers on AWS — approximately $10–11/month, $15 budget**

I would like approval to host the Ashoka Careers website for **jobs and internships** in
our AWS account. Staff will create/manage listings; applicants follow a staff-provided form
or website link, or open an email application with a preset subject. Supporting documents
remain hosted externally. The site will not collect applications, CVs or document uploads.

The proposed setup is a small dedicated server in Mumbai, with HTTPS and private daily
backups. It stores public listings and staff names, email addresses and Argon2 password
hashes. Access/security logs may contain visitor IP addresses. We need approval for that
data, its retention, public access and the external application/document providers.

### Resources and estimated costs

| Resource | Requested specification | Monthly USD, before tax |
|---|---|---:|
| Compute | One On-Demand Linux t4g.micro, 2 burstable vCPUs, 1 GiB RAM; Standard credits | $4.09 |
| Disk | 16 GB encrypted gp3, default performance | $1.46 |
| Public address | One Elastic IPv4 address | $3.65 |
| Data backups | Private Mumbai S3 prefix, daily archive, 30-day retention | Allow $1.00 |
| DNS | Subdomain in our existing zone | Confirm existing provider/query fees |
| HTTPS | Caddy automatic certificate renewal | $0 |
| **Base plus backup allowance** | **730-hour month; existing DNS** | **$10.20** |

Please approve a **$15/month pre-tax planning budget**, with $10/$15 alerts sent to us.
This is not a hard spending limit. If a new Route 53 hosted zone is required, allow another
$0.50/month plus queries. Traffic, paid monitoring, additional snapshots, taxes and currency
conversion can increase the bill; please confirm how they apply to our account. Pricing
was checked on 4 October 2026 and must be refreshed before deployment. No Free Tier,
promotional credits or organisation discounts are assumed.

Rates: [Mumbai compute/storage catalogue](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/ap-south-1/index.csv),
[public IPv4](https://aws.amazon.com/vpc/pricing/),
[DNS](https://aws.amazon.com/route53/pricing/) and [S3](https://aws.amazon.com/s3/pricing/).

If you prefer simpler bundled billing, the alternative is **Lightsail's $7/month Linux
public-IPv4 plan** (1 GB RAM, 40 GB disk, 1 TB Mumbai transfer), plus backups/overages.
We should select one hosting option. [Lightsail pricing](https://aws.amazon.com/lightsail/pricing/).

### Decisions and approvals I need

- **Account and billing:** approved account, Mumbai region, cost centre/tags, budget owner,
  applicable taxes/conversion, and permission to incur the agreed recurring charges.
- **Infrastructure:** permission for a dedicated instance, disk, one Elastic IP and a new
  security group in an approved public subnet. Please provision these yourself or delegate
  narrowly scoped creation access. Existing research instances/fleets will remain separate.
- **Public URL:** approved production and temporary staging hostnames; DNS owner and who
  will update records. Approval for public HTTPS access on ports 80/443 and certificate issuance.
- **Operator access:** my named login/role, MFA, and SSH from an approved IP/VPN or SSM;
  sudo on this server for installation, service management and patches. I do not need
  account-wide AdministratorAccess or root credentials.
- **Backups:** private S3 bucket/prefix, encrypted storage, versioning and lifecycle rules;
  instance upload role and designated restore operators. Please approve retention and a
  restore drill before launch. No AWS access keys will be embedded in the app.
- **Data and policy:** approval to store the staff account data listed above; who may create
  admins/reset passwords, log retention, and approved external forms/document hosts.
- **Operations:** named infrastructure owner, application maintainer and backup/alert recipient;
  patch schedule, recruitment-period traffic expectations and escalation contact.
- **Availability:** acceptance of a single-server setup and brief nightly backup/restart
  downtime. Daily backups target up to 24 hours' data loss; a 1–2 hour rebuild is a target to
  validate, not a guaranteed SLA. Higher availability needs a separately priced design.
- **Migration:** change window, staff editing freeze, DNS cutover/rollback owner, and approval
  to retire Vercel/Upstash only after AWS and its restore procedure are accepted.

The deployment instructions and service/backup templates are in
[AWS_MIGRATION.md](AWS_MIGRATION.md). I will deploy after these decisions are approved.

## Permission details for the AWS administrator

The simplest arrangement is **manager-provisioned AWS resources + limited operator access**.
The application itself needs no EC2 administration permissions. The list below describes
capabilities to scope; it is not an IAM policy to paste with wildcard access.

| Who | Capability / typical AWS actions | Scope and purpose |
|---|---|---|
| Manager/provisioner | EC2 `RunInstances`, `CreateTags`, `CreateSecurityGroup`, `AuthorizeSecurityGroupIngress`, `AllocateAddress`, `AssociateAddress`, `ModifyInstanceCreditSpecification`; relevant `Describe*` reads | Approved region/subnet, instance type, tags, security group, address and encrypted disk; apply account policy |
| Operator, if delegated | `DescribeInstances`, `DescribeInstanceStatus`, `DescribeVolumes`, `DescribeSecurityGroups`, `DescribeInstanceCreditSpecifications`; approved `StartInstances`, `StopInstances`, `RebootInstances` | New careers instance/resources only where IAM supports resource scope; reads often need broader resource scope with region conditions |
| SSM operator, if chosen | `ssm:StartSession`, `ResumeSession`, `TerminateSession`, relevant read actions | New instance, approved session document and own sessions; manager configures instance role/SSM connectivity |
| Provisioner attaching role | `iam:PassRole` and instance-profile association capabilities | Only the approved careers instance role; passed only to EC2, not arbitrary roles |
| Backup instance role | `s3:PutObject` | Only `APPROVED_BUCKET/kcdh-careers/*`; no delete, bucket administration or account access |
| Restore operator | `s3:ListBucket`, `GetObject`, optionally `GetObjectVersion` | List restricted to the careers prefix, read only its archives; never public |
| Manager/backup administrator | S3 bucket creation/configuration, public-access block, encryption, versioning, lifecycle | Dedicated approved bucket, or isolated prefix with an existing bucket's approved policies |
| DNS owner | Route 53 record-change/read access if DNS is there | Approved hosted zone and careers record names; manager can perform changes instead of delegating |
| Billing owner | Budget creation/updates, billing/Cost Explorer viewing | Manager retains this; provide project cost reports and agreed alerts |

SSM requires an appropriate instance role, e.g. the manager's approved equivalent of
[AmazonSSMManagedInstanceCore](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-getting-started-instance-profile.html).
SSE-S3 is assumed; if policy requires a customer-managed KMS key, approve its additional
key permissions and costs. Termination, IP release and backup deletion should remain with
the manager unless separately delegated. Lightsail needs a different service permission set.

During the read-only account check, EC2 inventory was accessible, but Cost Explorer,
Lightsail inventory and RDS inventory were denied. Those denials do not establish whether
the services exist or whether deployment is authorised. The manager should confirm the
account's policies and bill; the proposed plan does not need RDS access.

## Approval record to fill in

| Decision | Approved value / owner |
|---|---|
| EC2 or Lightsail; account and region | |
| Cost centre, monthly budget, alert recipients | |
| Production/staging domains and DNS owner | |
| Instance/subnet/security group and access method | |
| Maintainer role, OS access and instance backup role | |
| Backup bucket/prefix, retention and restore owner | |
| Application admin/contact, patch and log policy | |
| Availability/recovery targets and monitoring owner | |
| Cutover window, rollback owner and retirement approval | |
| Manager approval/date and approved release commit | |
