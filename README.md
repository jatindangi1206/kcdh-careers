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
server.py           backend, shared-store support, and account CLI
api/index.py        Vercel function entrypoint
vercel.json         static pages and API routing
internships.json    the postings — this is the database
auth.json           accounts: name + Argon2id password hash (git-ignored, chmod 600)
test_server.py      backend assertions + HTTP workflow checks
test_frontend.js    dependency-free rendering + session checks
```

Python standard library only, plus `argon2-cffi` for password hashing. Local development
uses JSON files; Vercel uses Upstash Redis through its REST API without another dependency.

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
maintainer, and the maintainer runs one command. With shared Redis these commands can run
while the site is live. For an AWS file deployment, use the locked maintenance procedure
in [AWS_MIGRATION.md](AWS_MIGRATION.md), avoiding overlapping account writes/backups.

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
- Local sessions live in memory, so restarting the local server signs everyone out.
  Production sessions live in Redis with a 12-hour expiry and survive Vercel restarts.

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

## 4. Deploying to Vercel + Upstash

The repository is <https://github.com/jatindangi1206/kcdh-careers>. The Vercel project is
`kcdh-careers`. `vercel.json` builds the static pages into `public/`, maps `/admin` to the
staff page, and sends `/api/*` to the existing Python handler. Functions run in Mumbai.
Only public assets are served statically; account files and environment files are excluded.

### 4.1 Persistent storage

Connect an **Upstash for Redis** database to the Vercel project's Production and Development
environments. Choose the **Free** plan with **automatic upgrades disabled** and **eviction
disabled**; keep its region near the function (Mumbai / `bom1`). Marketplace terms must be
accepted by the account owner before provisioning. Free-plan limits cause errors rather
than silently upgrading or discarding account/posting data.

The backend accepts either integration naming scheme:

- `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN`
- `KV_REST_API_URL` and `KV_REST_API_TOKEN`

`CAREERS_STORE_PREFIX` defaults to `kcdh-careers:`. Postings, accounts, sessions, and
failed-login counters are all shared in Redis. Atomic compare-and-set prevents one function
instance from overwriting another instance's update; a conflict asks staff to reload.
On Vercel, missing storage or an outage returns an error instead of falling back to temporary
files. HTTPS-only cookies are enabled automatically.

Use a separate database or prefix for Preview if staff need to test changes there. Do not
connect a preview to the live database inadvertently. With no Preview storage configured,
static pages work but the API deliberately reports storage not configured.

### 4.2 Production staff accounts

Pull the **Development** environment connected to the same database and run the existing
account CLI locally against it:

```bash
vercel env pull .env.local --environment development
set -a
. ./.env.local
set +a
.venv/bin/python server.py adduser you@ashoka.edu.in
```

Choose admin: yes for the maintainer. This creates a new production account; it does not
upload local `auth.json`. Passwords remain hashed. Use `users`, `passwd`, and `deluser` with
the same environment for account maintenance. Close this terminal afterwards to return to
local file storage. Never commit `.env.local` or paste its contents into an issue or chat.

Production starts with an empty board. Staff can create real listings after signing in;
the example `internships.json` is not automatically published or copied into Redis.

### 4.3 Deploy and maintain

```bash
.venv/bin/python test_server.py
node test_frontend.js
vercel deploy --prod
```

Connect the GitHub repository to Vercel for later automatic deployments. Keep private backups
of the Redis `postings` and `users` records; GitHub only backs up code. Deployment/restarts do
not reset postings or accounts. Optional `MAINTAINER_EMAIL` overrides the sign-in contact.

## 5. Routine maintenance

### Later migration to AWS

Follow [AWS_MIGRATION.md](AWS_MIGRATION.md) for server sizing, current Mumbai cost estimates,
copyable installation steps, Upstash data migration, HTTPS, backups and rollback. Use
[MANAGER_APPROVAL.md](MANAGER_APPROVAL.md) for the manager request, budget and scoped
permissions checklist. The initial EC2 plan is 1 GiB RAM, 2 burstable vCPUs and 16 GB disk:
about $9.20/month before backups/tax, with a suggested $15 pre-tax budget. Recheck pricing
before migration. These instructions do not change the Vercel deployment.

### Maintenance commands

| Task | Action |
|---|---|
| Add/reset/remove staff | Load the storage environment and run the account CLI above |
| View accounts | `.venv/bin/python server.py users` with the storage environment |
| Deploy code | Push to the connected GitHub repository, or `vercel deploy --prod` |
| Investigate errors | Check Vercel function logs and the Upstash database's status/limits |
| Test shared storage | `.venv/bin/python test_shared_store.py` (local `redis-server` / `redis-cli` required) |

Local development still uses the JSON files unless storage environment variables are set.
`DATA_DIR` can point local file storage to another existing directory. Stop the local server
before editing its JSON files by hand. Production writes must go through the app or account
CLI; do not overwrite Redis records while staff are editing postings.

---

## 6. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `ModuleNotFoundError: argon2` | Wrong interpreter. Use `.venv/bin/python`, not `python`. |
| `mach-o ... incompatible architecture` (macOS) | The x86_64 python.org 3.10 build. Rebuild the venv with `/opt/homebrew/bin/python3.13`. |
| `Port 8000 is already in use` | Another copy is running. `lsof -ti :8000 \| xargs kill`, or `PORT=8001`. |
| Staff say the site logged them out | The local server restarted or the 12-hour session expired. Sign in again. |
| A posting vanished from the public page | Its deadline passed, or it was archived. It is still in `/admin`. |
| "That posting belongs to someone else" | Correct — only the owner or an admin can change it. |
| Google Form link rejected | They copied the `/edit` URL. Forms → Send → link icon → Copy. |
| Locked out after many wrong passwords | Ten failures from one IP blocks that IP for five minutes. Wait. |

---

## 7. Handing this over

Everything a successor needs: this README, repository access, Vercel/Upstash access, and
the database backup location.
There is no frontend framework or CI; Vercel serves static files and one Python function,
and Redis holds production state. `server.py` remains a single module that can be read end to end.

Deliberately **not** built, and worth resisting: applications stored in this app, CV uploads,
applicant email notifications, an approval workflow. Google Forms already does all of that,
and every one of them would bring a database, file storage and a privacy obligation with it.

The natural next step, when Ashoka IT can register an OAuth client, is **Sign in with Google
restricted to `@ashoka.edu.in`**. That deletes `auth.json` and the password resets entirely —
staff use the Ashoka login they already have, and IT disabling someone removes their access
automatically. The per-owner model above carries over unchanged.
