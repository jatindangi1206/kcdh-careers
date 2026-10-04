# Ashoka Careers

Jobs and internships board for **Ashoka University**. Staff sign in, post an opportunity,
and it appears on the public page
immediately — no rebuild, no deploy, no code.

Applicants apply through a **staff-provided form / website link** or **email**. The email
button opens their email app with a recipient and subject; this site never stores applicant data.

```
static/index.html   public listing + search, type, centre and category filters
static/admin.html   staff sign-in + add/edit/archive/delete
static/style.css    shared styles
static/listing.js   shared public card + staff preview renderer
server.py           the whole backend, plus the account CLI
internships.json    the postings — this is the database
auth.json           accounts: name + Argon2id password hash (git-ignored, chmod 600)
test_server.py      backend assertions + HTTP workflow checks
test_frontend.js    dependency-free rendering + session checks
```

Python standard library only, plus `argon2-cffi` for password hashing.

---

## 1. Running it locally

```bash
/opt/homebrew/bin/python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt

.venv/bin/python server.py adduser you@ashoka.edu.in   # first account — say yes to admin
.venv/bin/python server.py                             # http://localhost:8000
```

Public page <http://localhost:8000/> · Staff sign-in <http://localhost:8000/admin>

> **Always call `.venv/bin/python` by its full path.** Do not `activate` and type `python`.
> Shell aliases and the x86_64 python.org build in `/Library/Frameworks` both shadow the
> venv, and the wrong interpreter fails with `ModuleNotFoundError: argon2` or
> `mach-o ... incompatible architecture`. The venv itself must be created from an arm64
> Python (`/opt/homebrew/bin/python3.13`) for the same reason.

Run the backend check: `.venv/bin/python test_server.py` → prints `ok`.
Run the frontend logic check (Node.js): `node test_frontend.js` → prints `frontend ok`.
These use temporary data and do not change your postings or accounts. Frontend checks do
not replace checking the layout and keyboard interactions in a browser.

---

## 2. Accounts

Every faculty member or staff member gets their own email + password. **They can only see
and edit their own postings.** An admin account sees and edits everyone's.

There is no self-service sign-up and no password-reset email — by design. People ask the
maintainer, and the maintainer runs one command. All four commands are safe to run while
the site is live.

```bash
.venv/bin/python server.py users                    # list accounts
.venv/bin/python server.py adduser a.rao@ashoka.edu.in   # prompts name, admin?, password
.venv/bin/python server.py passwd  a.rao@ashoka.edu.in   # reset a forgotten password
.venv/bin/python server.py deluser a.rao@ashoka.edu.in   # remove an account
```

`adduser` asks whether the account is an admin. Say **no** for ordinary faculty — admin is
for whoever maintains the site.

Notes:

- Passwords must be at least 12 characters. Give the person a temporary one over a channel
  they already trust, and run `passwd` again whenever they ask.
- Emails are case-insensitive.
- Deleting an account leaves that person's postings in place; they become admin-only.
  Delete or reassign the postings first if that matters.
- Only the Argon2id **hash** is stored. The password itself exists nowhere — not in
  `auth.json`, not in any HTML or JavaScript, not in the browser. If someone forgets it,
  nobody can look it up; you reset it.
- Sessions live in memory, so restarting the server signs everyone out. Harmless.

---

## 3. What a faculty member does

1. Go to `/admin` and sign in. Existing postings appear first; filter by Active, Archived,
   Expired, or All postings. Click **Add opportunity** or **Edit**.
2. Choose **Job** or **Internship**, then enter a title, deadline, and short summary. Add optional **Full details** for project
   background, responsibilities, or application instructions. Paragraphs are preserved.
3. Choose **Form / website** and paste your application URL, or choose **Email** and enter
   the recipient and an optional subject. An empty subject defaults to `Application: <title>`.
4. For Google Forms, create your own form and copy its respondent link, not its `/edit` URL.
5. Optionally enter a **Document title** and **Document link** for a PDF or Word file hosted
   on Drive or a university site. Ensure applicants can open it without requesting access.
   Documents are linked, not uploaded to this server.
6. Click **Preview listing** to check the public card, then **Add opportunity** or **Save changes**.

Public cards label each opportunity as Job or Internship and show the summary and key facts.
Both public and staff pages can filter by opportunity type. Existing records without a type
default to Internship; the `internships.json` filename and API routes stay compatible. **Read more** expands full details and document
links in place, with **Apply** below them. Email applications include a copyable address.
A form / website application opens in a new tab. The site does not send emails itself.

Published postings require an application destination. **No destination** is available only
for archived postings; old postings remain readable without a data migration. Links and dates
are validated on the server, including rejecting Google Form editing links.

Deadlines use **Asia/Kolkata** for both public visibility and staff status. Postings disappear
from the public page the day after their deadline. **Archive** hides a posting early while
keeping it; **Delete** is permanent. Unsaved changes trigger a warning when leaving, and an
expired session preserves entered text while the staff member signs in again. Drafts are not
stored across closing the tab or restarting the browser.

The sign-in page links to the first admin account's email. Set `MAINTAINER_EMAIL` to override
that contact, for example `MAINTAINER_EMAIL=help@ashoka.edu.in .venv/bin/python server.py`.

---

## 4. Putting it on the internet (AWS)

The app is a long-running process that writes to a file on disk, so it needs an ordinary
Linux machine with an ordinary disk: **EC2 or Lightsail**. Not Lambda, App Runner, Fargate
or Amplify — those have no persistent filesystem and would silently lose every posting.

A **t4g.micro** (or the $5 Lightsail plan) with the default 8 GB disk is far more than
enough: the data is a few kilobytes.

### 4.1 Instance

- Ubuntu 24.04, arm64.
- Security group: **443** and **80** open to the world; **22 only from your own IP**.
- Attach an **Elastic IP** (or Lightsail's static IP) *before* giving DNS the address —
  a plain EC2 public IP changes on every stop/start and would break the site.
- Ask Ashoka IT for a subdomain (e.g. `internships.ashoka.edu.in`) pointing at that IP.
- **Beware `DeleteOnTermination`** — it is on by default. Terminating the instance destroys
  the disk and every posting with it. *Stopping* is safe; *terminating* is not.

### 4.2 Install

```bash
ssh ubuntu@<elastic-ip>

sudo apt update && sudo apt install -y python3-venv git caddy
sudo mkdir -p /srv/internships && sudo chown ubuntu:ubuntu /srv/internships
git clone <your-repo-url> /srv/internships    # or: scp -r ./ ubuntu@<ip>:/srv/internships
cd /srv/internships
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python server.py adduser you@ashoka.edu.in     # admin: yes
```

Create the accounts **on the server**. Never copy your local `auth.json` up; it is
git-ignored for that reason.

### 4.3 Keep it running — `/etc/systemd/system/internships.service`

```ini
[Unit]
Description=Ashoka careers board
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/srv/internships
Environment=SECURE_COOKIE=1
ExecStart=/srv/internships/.venv/bin/python server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now internships
sudo systemctl status internships       # check it is running
journalctl -u internships -f            # watch the log
```

`SECURE_COOKIE=1` makes the session cookie HTTPS-only. Set it in production, never locally.

### 4.4 HTTPS — `/etc/caddy/Caddyfile`

```
internships.ashoka.edu.in {
    reverse_proxy 127.0.0.1:8000
}
```

```bash
sudo systemctl reload caddy
```

Caddy obtains and renews the certificate on its own. The app binds `127.0.0.1`, so it is
reachable only through Caddy. Caddy also sets `X-Forwarded-For`, which the app reads so the
failed-login lockout counts real visitors rather than the proxy.

### 4.5 Backups — do not skip

`internships.json` and `auth.json` are the only copies of the data. Create an S3 bucket with
**versioning on**, attach an IAM instance role that can write to it (no access keys on
disk), then `sudo crontab -e`:

```cron
0 2 * * * aws s3 cp /srv/internships/internships.json s3://ashoka-internships-backup/ && aws s3 cp /srv/internships/auth.json s3://ashoka-internships-backup/
```

Restore is a copy back and `sudo systemctl restart internships`. EBS snapshots are worth
having too, but versioned S3 is what gives you "last Tuesday's file" in one command.

---

## 5. Routine maintenance

| Task | Command (on the server, in `/srv/internships`) |
|---|---|
| A professor wants an account | `.venv/bin/python server.py adduser <email>` |
| Someone forgot their password | `.venv/bin/python server.py passwd <email>` |
| Someone has left Ashoka | `.venv/bin/python server.py deluser <email>` |
| Who has an account? | `.venv/bin/python server.py users` |
| Is the site up? | `sudo systemctl status internships` |
| Something looks wrong | `journalctl -u internships -n 100` |
| Restart after a config change | `sudo systemctl restart internships` |
| Deploy new code | `git pull && sudo systemctl restart internships` |

Postings are plain JSON — `internships.json` can be edited by hand in an emergency. Stop the
service first, edit, restart. Keep it valid JSON.

---

## 6. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `ModuleNotFoundError: argon2` | Wrong interpreter. Use `.venv/bin/python`, not `python`. |
| `mach-o ... incompatible architecture` (macOS) | The x86_64 python.org 3.10 build. Rebuild the venv with `/opt/homebrew/bin/python3.13`. |
| `Port 8000 is already in use` | Another copy is running. `lsof -ti :8000 \| xargs kill`, or `PORT=8001`. |
| Staff say the site logged them out | The server restarted. Sessions are in memory. They sign in again. |
| A posting vanished from the public page | Its deadline passed, or it was archived. It is still in `/admin`. |
| "That posting belongs to someone else" | Correct — only the owner or an admin can change it. |
| Google Form link rejected | They copied the `/edit` URL. Forms → Send → link icon → Copy. |
| Locked out after many wrong passwords | Ten failures from one IP blocks that IP for five minutes. Wait. |

---

## 7. Handing this over

Everything a successor needs: this README, SSH access to the instance, and the AWS account.
There is no build step, no framework, no database and no CI. `server.py` remains a single module that can be read end to end.

Deliberately **not** built, and worth resisting: applications stored in this app, CV uploads,
applicant email notifications, an approval workflow. Google Forms already does all of that,
and every one of them would bring a database, file storage and a privacy obligation with it.

The natural next step, when Ashoka IT can register an OAuth client, is **Sign in with Google
restricted to `@ashoka.edu.in`**. That deletes `auth.json` and the password resets entirely —
staff use the Ashoka login they already have, and IT disabling someone removes their access
automatically. The per-owner model above carries over unchanged.
