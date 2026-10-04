# Optional EC2 Migration Runbook

This is the **paid, always-on fallback**, not the recommended starting plan. Begin with the
free-first options in [AWS_MIGRATION.md](AWS_MIGRATION.md). Use this runbook only if the
manager specifically approves a virtual machine instead of serverless hosting.

Use this when the manager approves moving Ashoka Careers from Vercel + Upstash to EC2.
This is a future deployment plan; adding this document does not create AWS resources.
The [manager draft](MANAGER_APPROVAL.md) now requests serverless hosting; for this VM
fallback, request separate approval using the EC2 resource/cost table below. Publish this guide and `deploy/aws/`
templates in the approved Git release before cloning it below. Record the approved account, domain,
instance ID, backup bucket, cost centre, and release commit in the team's private handover.

## 1. Size and architecture

Start with **one EC2 `t4g.micro`: 2 burstable vCPUs, 1 GiB RAM, 16 GB encrypted gp3 disk**
in Mumbai (`ap-south-1`), running Ubuntu Server 24.04 LTS **ARM64**, without Ubuntu Pro.
This is an initial low-traffic sizing recommendation, not a measured capacity guarantee.
Avoid 512 MB: the OS, HTTPS proxy, and concurrent Argon2 password checks need headroom.

```text
Visitor / staff → approved domain → Elastic IP → Caddy HTTPS :443
                                               → Python 127.0.0.1:8000
                                               → /var/lib/kcdh-careers/*.json
                                               → private S3 daily backup
```

- Code lives in `/srv/kcdh-careers`; data lives outside Git in `/var/lib/kcdh-careers`.
- Run **one Python process on one server**. File storage is not a shared database for an
  autoscaling group or multiple workers. Staff sessions reset on restart.
- The app stores job/internship descriptions, application/document URLs, and staff names,
  emails and password hashes. It does not receive CVs, files, or applications. Forms and
  documents remain with their external providers.
- Example estimate: 1,000 postings averaging 5 KB require about 5 MB; 16 GB mainly allows
  room for Linux, dependencies and bounded logs. This estimate is not a posting limit.
- No RDS, managed Redis, load balancer, NAT gateway, containers, or paid SSL certificate is
  required for this single-server plan. If institutional policy requires those, reprice it.

Choose **Standard CPU credit mode explicitly**. T4g normally defaults to Unlimited.
Standard avoids surplus-credit bills, but throttles after credits run out; the micro has a
10% baseline per vCPU. Check CPU credits, RAM, disk and response times after launch and
before a recruitment announcement. Resize if sustained load or memory pressure warrants it.
See [AWS CPU credit documentation](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-credits-baseline-concepts.html).

## 2. Monthly cost to approve

Public Mumbai rates checked **4 October 2026**; Linux On-Demand, 730 hours/month, USD,
before taxes, currency conversion, discounts and credits. These are new-resource estimates,
not the account's actual bill; Cost Explorer access was denied during the account check.

| Item | Calculation | Monthly estimate |
|---|---|---:|
| EC2 t4g.micro compute | $0.0056/hour × 730 | $4.09 |
| Encrypted gp3 disk, default IOPS/throughput | 16 GB × $0.0912/GB-month | $1.46 |
| One Elastic/public IPv4 address | $0.005/hour × 730 | $3.65 |
| **Server + disk + IP** | | **$9.20** |
| Daily small S3 data backups and requests | Planning allowance, not a fixed service price | $1.00 |
| DNS using an existing university zone | No new zone; provider/query costs may apply | Confirm |
| New Route 53 zone, only if needed | $0.50/month, plus queries | $0.50 + usage |
| HTTPS certificate | Caddy automatic HTTPS | $0 |

**Request a $15/month pre-tax operating budget** for low traffic with existing DNS and
small backups. It is a planning allowance, not a spending cap. Budget alerts at $10 and $15
should go to the manager and maintainer. Ask the manager to confirm taxes, exchange rate,
network charges, monitoring charges and account-level discounts before approval.

AWS offers 100 GB/month internet egress aggregated across eligible services/regions; the
existing account may already use it. Traffic above available allowance costs extra. Optional
EBS snapshots are **$0.05 per GB-month stored** in Mumbai, with changing blocks/retention
affecting the total; they are not included above. Paid CloudWatch alarms/log ingestion,
custom KMS keys, domain purchase, WAF and support plans also need separate approval.
Stopping EC2 stops compute billing, but retained disks, snapshots and allocated IPs still cost.

Sources: [official Mumbai EC2/EBS rate catalogue](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/ap-south-1/index.csv),
[IPv4 pricing](https://aws.amazon.com/vpc/pricing/),
[EC2 transfer and CPU pricing](https://aws.amazon.com/ec2/pricing/on-demand/),
[S3 pricing](https://aws.amazon.com/s3/pricing/), and
[Route 53 pricing](https://aws.amazon.com/route53/pricing/).
Recheck rates in the [AWS calculator](https://calculator.aws/) before deploying later.

### Simpler billing alternative

If the manager prefers Lightsail, its **$7/month Linux public-IPv4 bundle** provides 1 GB
RAM, 2 vCPUs, 40 GB SSD and **1 TB transfer in Mumbai** (half the advertised 2 TB).
The bundle includes DNS management and an attached static IP; snapshots and transfer
overages are extra. Allow approximately **$8–10/month before tax** with small backups.
Do not add EC2 disk/IP charges to this bundle. The Linux application steps below still
apply, but Lightsail networking, access and backup setup must replace the EC2-specific steps.
EC2 is the documented default because it fits the existing account's EC2/IAM operations.
[Official Lightsail pricing](https://aws.amazon.com/lightsail/pricing/).

## 3. Manager provisions the infrastructure

After written approval, ask the manager to:

1. Launch the instance above in an approved **public subnet**, with a route through an
   internet gateway, Standard credits, encrypted root disk, IMDSv2 required, and tags
   `Project=kcdh-careers`, `Owner=<maintainer>`, `Environment=production` and cost centre.
   Confirm root-volume deletion policy and backups before eventual termination.
2. Associate one Elastic IP. Allow TCP 80/443 publicly. Allow SSH 22 only from an approved
   administrator IP/VPN, or use approved SSM access. Never expose port 8000 or open SSH
   to everyone. No new NAT gateway is needed for this public-subnet design.
3. Supply OS administration access, GitHub access to an approved release, and a staging
   hostname for HTTPS checks. Retain DNS control or delegate only the required records.
4. Create a private S3 backup bucket/prefix in Mumbai: block all public access, default
   SSE-S3 encryption, versioning and a lifecycle retaining daily archives for 30 days.
   Include noncurrent-version expiry and expired-delete-marker cleanup. Legal retention
   requirements take precedence over this suggested 30-day policy.
5. Attach an instance role limited to writing that backup prefix; give restore read access
   only to approved operators. Do not put IAM access keys on disk. Install AWS CLI v2 for
   the instance architecture using [AWS installation instructions](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).
6. Configure budget alerts and agree who handles patches, backup failures and downtime.
   Enable SSM only with the manager-approved instance role/connectivity if that is the
   account's access standard. Do not modify existing research instances or security groups.

## 4. Install the application on Ubuntu

Run these commands **on the new server**, with sudo access. They intentionally do not copy
your Mac virtual environment, local accounts or example postings.

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv git caddy curl cron
sudo adduser --system --group --home /var/lib/kcdh-careers careers
sudo install -d -o careers -g careers -m 700 /var/lib/kcdh-careers
sudo git clone https://github.com/jatindangi1206/kcdh-careers.git /srv/kcdh-careers
cd /srv/kcdh-careers
git rev-parse HEAD                         # compare with the approved release
sudo python3 -m venv .venv
sudo .venv/bin/pip install -r requirements.txt
sudo .venv/bin/python test_server.py        # temporary data, not production
```

Keep code/venv owned by the administrator; the `careers` service user needs read access
there and write access only to its data directory. If the release is a specific commit,
have the manager check it out before installation. For Caddy package alternatives, see
[official installation instructions](https://caddyserver.com/docs/install).

Create `/etc/kcdh-careers.env` using `sudoedit`, mode 600, with:

```ini
DATA_DIR=/var/lib/kcdh-careers
SECURE_COOKIE=1
PORT=8000
MAINTAINER_EMAIL=REPLACE_WITH_APPROVED_CONTACT
```

Replace the contact. **Do not copy `.env.local`.** Omit `VERCEL`,
`UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`, `KV_REST_API_URL` and
`KV_REST_API_TOKEN`: any of those selects Redis rather than AWS file storage.

## 5. Prepare data: choose exactly one path

### A. No live production data yet

Initialize empty postings and create a new production maintainer account:

```bash
sudo -u careers sh -c 'umask 077; printf "[]\n" > /var/lib/kcdh-careers/internships.json'
cd /srv/kcdh-careers
sudo -u careers env DATA_DIR=/var/lib/kcdh-careers .venv/bin/python server.py adduser you@ashoka.edu.in
```

Replace the email; choose admin: yes. Do not run the initialization over existing data.
The checked-in examples and local `auth.json` are not production data.

### B. Production Vercel + Upstash already contains data

Agree a staff editing freeze, including account CLI changes. Keep it in effect until
cutover is verified. Load the **live database's** environment locally as described in the
main README; confirm the database and `CAREERS_STORE_PREFIX` before exporting. Never
export a Preview database by mistake. From the local repository:

```bash
.venv/bin/python - <<'PY'
import json, os
from pathlib import Path
import server

assert server.REMOTE and server.REDIS_URL and server.REDIS_TOKEN, 'Load the live Upstash environment first'
posts, accounts = server.redis('MGET', server.PREFIX + 'postings', server.PREFIX + 'users')
assert accounts is not None, 'No live accounts found; verify database/prefix'
posts = json.loads(posts) if posts is not None else []
accounts = json.loads(accounts)
assert isinstance(posts, list) and isinstance(accounts, dict)
out = Path.home() / 'kcdh-aws-export'
out.mkdir(mode=0o700)  # fails if it already exists; protects a previous export
for name, value in [('internships.json', posts), ('auth.json', {'users': accounts})]:
    with os.fdopen(os.open(out / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as f:
        json.dump(value, f, indent=2)
print('Private export saved; postings:', len(posts), 'accounts:', len(accounts))
PY
```

Transfer these two private files using the approved SSH/SCP or private S3 channel. On the
server, install them from that private staging directory (replace the source paths):

```bash
sudo install -o careers -g careers -m 600 /PRIVATE/STAGING/internships.json /var/lib/kcdh-careers/internships.json
sudo install -o careers -g careers -m 600 /PRIVATE/STAGING/auth.json /var/lib/kcdh-careers/auth.json
```

Preserve record IDs, ownership and password hashes. Do not import sessions or login-failure
counters; staff sign in again. Keep the export private and remove transfer copies after
verified backup/restore. Export again at final cutover if staff were allowed to edit after a
rehearsal. Never let both AWS and Vercel accept staff writes during transition.

## 6. Start the service and HTTPS

```bash
cd /srv/kcdh-careers
sudo chmod 600 /etc/kcdh-careers.env
sudo install -m 644 deploy/aws/kcdh-careers.service /etc/systemd/system/kcdh-careers.service
sudo systemctl daemon-reload
sudo systemctl enable --now kcdh-careers
curl --fail http://127.0.0.1:8000/api/internships
```

Have the manager point the staging hostname's DNS A record to the Elastic IP. Remove any
conflicting AAAA record unless IPv6 is configured. Edit `deploy/aws/Caddyfile` to that hostname,
then install it below **only on this new dedicated server**. On a shared proxy, the manager
must merge the site block rather than replace an existing configuration.

```bash
sudo install -m 644 deploy/aws/Caddyfile /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl enable --now caddy
sudo systemctl reload caddy
```

Caddy obtains/renews HTTPS once public DNS and ports 80/443 work. TLS terminates at Caddy;
Python remains private on localhost. Staff login must be tested through **HTTPS** because
the session cookie is Secure. See [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https).

## 7. Backups before going live

The supplied `deploy/aws/backup.sh` briefly stops Python to archive consistent JSON files,
restarts it **before** uploading, and records the release commit. Restart signs staff out.
Schedule outside staff hours; account maintenance must not overlap the backup lock.

Create root-only `/etc/kcdh-careers-backup.env` (mode 600), replacing the bucket:

```ini
BACKUP_S3_URI=s3://APPROVED_PRIVATE_BUCKET/kcdh-careers
AWS_DEFAULT_REGION=ap-south-1
```

```bash
sudo install -m 700 /srv/kcdh-careers/deploy/aws/backup.sh /usr/local/sbin/kcdh-careers-backup
sudo /usr/local/sbin/kcdh-careers-backup       # verify successful upload now
```

Have the manager confirm the role's prefix-only upload permission and bucket encryption.
Create `/etc/cron.d/kcdh-careers-backup` mode 644 with a final newline:

```cron
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
0 20 * * * root /usr/local/sbin/kcdh-careers-backup >> /var/log/kcdh-careers-backup.log 2>&1
```

This runs at **20:00 UTC / 01:30 IST** if the server uses UTC; confirm with `timedatectl`.
Ensure cron is enabled. Add weekly rotation (four compressed copies) for that backup log
and cap journald disk usage, e.g. `SystemMaxUse=100M`, through the manager's logging policy.
Check daily that a new S3 archive exists and arrange a failure alert using existing monitoring.
The script is a backup mechanism, not an alerting service. S3 lifecycle limits retention.

Local template check: `.venv/bin/python test_aws_backup.py` simulates service/S3 success,
upload failure and invalid data; it does not access AWS or stop a real service. Run the
actual upload and restore drill above on the approved server as well.

**Restore drill:** with the operator's S3 read permission, download an archive privately,
extract it to a mode-700 directory, validate both JSON files, and restore to a spare server
using step 5's `install` commands. Verify accounts, ownership and postings through HTTPS.
Record how long rebuilding took; only then agree recovery targets. Target daily backups
(up to 24 hours' data loss) and a 1–2 hour restore are goals, not guaranteed SLAs.

## 8. Cutover checklist and rollback

- [ ] Check public search/type filters, expanded details, documents, form links and email links.
- [ ] Check staff login, job/internship publishing, editing, archive, deletion and owner limits.
- [ ] Check logout and failed-login handling; `/auth.json`, `/.env` and `/server.py` return 404.
- [ ] Restart Python and verify postings/accounts remain; staff will need to sign in again.
- [ ] Confirm no public port 8000, valid HTTPS, successful backup and a tested restore.
- [ ] Lower the production DNS TTL ahead of migration, e.g. 300 seconds; agree a change window.
- [ ] Freeze old staff writes, take the final export, install it while AWS Python is stopped,
      restart, add the production hostname to Caddy, and update DNS. Keep the old service
      available for public reads during propagation; prevent staff edits there.
- [ ] Verify the production hostname and then release the staff freeze **on AWS only**.

Before AWS accepts new writes, rollback can restore the previous DNS/proxy destination.
After AWS has new postings/account changes, freeze writes again and reconcile/copy the
latest AWS data into the old store before rollback; changing DNS alone would lose updates.
Keep Vercel/Upstash and the migration export until the manager accepts the deployment and
restore drill. Retire old resources later by explicit agreement, including their secrets.

## 9. Maintenance and handover

View status/logs with `sudo systemctl status kcdh-careers` and
`sudo journalctl -u kcdh-careers --since today`. Review Caddy and backup logs separately.
Patch Ubuntu/dependencies in an agreed window and verify backups before every release.

For account changes or a release, first take a backup, then open this maintenance shell.
Its lock prevents overlapping backups; exit it when finished:

```bash
sudo flock /run/lock/kcdh-careers-maintenance.lock bash
trap 'systemctl start kcdh-careers' EXIT
systemctl stop kcdh-careers
cd /srv/kcdh-careers
sudo -u careers env DATA_DIR=/var/lib/kcdh-careers .venv/bin/python server.py users
# Account change: replace "users" with adduser/passwd/deluser and the staff email.
# Code update: git fetch origin, check out the approved commit, reinstall requirements.
# Run .venv/bin/python test_server.py before starting an updated release.
exit
```

Never run two account writers, overwrite live JSON, or copy production data into Git.
Retain the previous release commit for code rollback, keeping current data and a backup.
Assign named owners for staff password resets, Linux patches, DNS, costs and restore drills.
Memory/disk usage requires OS monitoring; basic EC2 metrics do not include those by default.
Ask for more capacity if measurements justify it; multiple app instances require shared
storage and a new deployment plan.
