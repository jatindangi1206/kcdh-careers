# Repository Guidelines

## Project Structure & Module Organization

Python careers board for jobs and internships, using plain HTML/CSS/JavaScript. `server.py` contains the HTTP server, authentication, posting storage, and account CLI. `static/index.html` renders public listings; `static/admin.html` manages staff postings; `static/style.css` provides shared styles; `static/listing.js` shares card rendering with staff previews. `internships.json` stores local postings; Upstash Redis stores production state. `auth.json` stores local accounts and hashes and must remain untracked. `test_server.py`, `test_frontend.js`, and `test_shared_store.py` contain checks. `README.md` documents operation and deployment.

## Build, Test, and Development Commands

Local development has no build step. On macOS:

```bash
/opt/homebrew/bin/python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python server.py adduser you@ashoka.edu.in
.venv/bin/python server.py
.venv/bin/python test_server.py
node test_frontend.js
```

These commands create the environment, install dependencies, create an account, serve the app at `http://localhost:8000`, and run backend and frontend checks (Node.js required for the latter). Always use `.venv/bin/python` explicitly to avoid interpreter conflicts. Use `PORT=8001 .venv/bin/python server.py` for another port. Account maintenance uses the `users`, `passwd <email>`, and `deluser <email>` subcommands.

## Coding Style & Naming Conventions

Match existing formatting: four-space Python indentation and two-space HTML, CSS, and JavaScript indentation. Use Python `snake_case`, JavaScript `camelCase`, and uppercase constants such as `FIELDS`. Keep the frontend and backend posting field lists aligned. No formatter or linter is configured. Prefer standard-library and native browser features; reuse existing helpers before adding dependencies or abstractions.

## Testing Guidelines

Tests use plain Python assertions, without a framework or coverage threshold. Run `.venv/bin/python test_server.py`; success prints `ok`. Extend checks for validation, visibility, ownership, persistence, or authentication. Shared-store checks require local Redis. Use temporary files rather than live data. Frontend checks use Node.js built-ins. For interface changes, manually check public filters and staff workflows, including owner restrictions.

## Commit & Pull Request Guidelines

The repository currently has one initial commit, so no established commit convention exists yet. Use concise imperative messages, such as `Validate internship deadlines`. PRs should describe the problem, resulting behavior, and validation performed. Link relevant issues and include screenshots for visible UI changes.

## Security & Configuration

Never commit credentials, `auth.json`, `.env*`, or `.venv/`. Preserve ownership checks, password hashing, and cookie protections. Set `SECURE_COOKIE=1` behind production HTTPS; `MAINTAINER_EMAIL` overrides the contact link. `api/index.py` and `vercel.json` deploy the existing handler to Vercel. Local writes retain locking/atomic replacement; Redis writes retain compare-and-set. Stop the local server before editing its JSON. Back up production Redis records before maintenance.
