"""Ashoka University careers board.

Run:   .venv/bin/python server.py                 # serve on :8000
Users: .venv/bin/python server.py adduser <email> # create a staff account
       .venv/bin/python server.py passwd  <email> # reset a password
       .venv/bin/python server.py deluser <email> # remove an account
       .venv/bin/python server.py users            # list accounts
"""
import http.cookies, json, os, re, secrets, sys, threading, time
from datetime import date, datetime
from zoneinfo import ZoneInfo
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

from argon2 import PasswordHasher

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "internships.json")
AUTH = os.path.join(HERE, "auth.json")
PORT = int(os.environ.get("PORT", 8000))
SECURE_COOKIE = os.environ.get("SECURE_COOKIE") == "1"  # set behind HTTPS
SESSION_HOURS = 12

ph = PasswordHasher()
lock = threading.Lock()
sessions = {}  # token -> (email, expiry). ponytail: in-memory, restart = everyone logged out.
fails = {}     # ip -> (count, first_fail_epoch)

FIELDS = ("title", "faculty", "department", "centre", "description", "eligibility",
          "duration", "deadline", "category", "apply_url", "details", "posting_type",
          "application_method", "apply_email", "email_subject", "document_title", "document_url")

# ---------- data ----------

def load():
    try:
        with open(DATA) as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save(items):
    tmp = DATA + ".tmp"
    with open(tmp, "w") as f:
        json.dump(items, f, indent=2)
    os.replace(tmp, DATA)  # atomic: a crash mid-write can't truncate the real file

def public(items, today=None):
    """Live opportunities: not archived, deadline today or later (ISO dates sort as strings)."""
    today = today or board_today()
    return [i for i in items if not i.get("archived") and i.get("deadline", "") >= today]

def board_today():
    return datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()

def web_url(value, label):
    parsed = urlparse(value)
    if (parsed.scheme not in ("http", "https") or not parsed.hostname
            or parsed.username or parsed.password or any(c.isspace() for c in value)):
        raise ValueError(f"{label} must be a complete http:// or https:// link.")
    if parsed.hostname == "docs.google.com" and parsed.path.startswith("/forms/") and "/edit" in parsed.path:
        raise ValueError("Use the Google Form respondent link: click Send, then the link icon, and copy that link.")

def clean(body):
    if not isinstance(body, dict):
        raise ValueError("Expected a JSON object.")
    out = {}
    for k in FIELDS:
        value = body.get(k, "")
        if not isinstance(value, str):
            raise ValueError(f"{k} must be text.")
        out[k] = value.strip()
    out["posting_type"] = out["posting_type"] or "internship"
    if out["posting_type"] not in ("job", "internship"):
        raise ValueError("Choose Job or Internship as the opportunity type.")
    out["archived"] = bool(body.get("archived"))
    if not out["title"] or not out["deadline"]:
        raise ValueError("Title and application deadline are required.")
    try:
        if date.fromisoformat(out["deadline"]).isoformat() != out["deadline"]:
            raise ValueError()
    except ValueError:
        raise ValueError("Use a valid deadline in YYYY-MM-DD format.")
    # Existing postings may use mailto links or have no application destination.
    if "application_method" not in body:
        if out["apply_url"].startswith("mailto:"):
            parsed = urlparse(out["apply_url"])
            out["application_method"] = "email"
            out["apply_email"] = unquote(parsed.path)
            out["email_subject"] = parse_qs(parsed.query).get("subject", [""])[0]
        else:
            out["application_method"] = "url" if out["apply_url"] else "none"
    method = out["application_method"]
    if method == "url":
        web_url(out["apply_url"], "Application link")
        out["apply_email"] = out["email_subject"] = ""
    elif method == "email":
        if not re.fullmatch(r"[^\s@?&#]+@[^\s@?&#]+\.[^\s@?&#]+", out["apply_email"]):
            raise ValueError("Enter a valid application email address.")
        if "\r" in out["email_subject"] or "\n" in out["email_subject"]:
            raise ValueError("Email subject must be one line.")
        out["apply_url"] = ""
    elif method == "none":
        if not out["archived"]:
            raise ValueError("Choose an application method before publishing, or archive this posting.")
        out["apply_url"] = out["apply_email"] = out["email_subject"] = ""
    else:
        raise ValueError("Choose a form / website or email application method.")
    if out["document_url"]:
        web_url(out["document_url"], "Document link")
    elif out["document_title"]:
        raise ValueError("Add a link for the supporting document.")
    return out

# ---------- accounts ----------

def users():
    try:
        with open(AUTH) as f:
            return json.load(f)["users"]
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return {}

def save_users(u):
    with open(AUTH, "w") as f:
        json.dump({"users": u}, f, indent=2)
    os.chmod(AUTH, 0o600)

def whoami(handler):
    """The signed-in user's record plus their email, or None."""
    tok = http.cookies.SimpleCookie(handler.headers.get("Cookie", "")).get("sid")
    s = sessions.get(tok.value) if tok else None
    if not s or s[1] <= time.time():
        return None
    u = users().get(s[0])
    return dict(u, email=s[0]) if u else None  # account deleted mid-session -> signed out

def check_password(email, pw, ip):
    n, since = fails.get(ip, (0, 0))
    if time.time() - since >= 300:
        n, since = 0, 0
    if n >= 10 and time.time() - since < 300:
        return False  # locked out for 5 minutes
    try:
        ph.verify(users()[email]["hash"], pw)
    except Exception:  # unknown email and wrong password fail identically
        fails[ip] = (n + 1, since or time.time())
        return False
    fails.pop(ip, None)
    return True

def may_edit(user, item):
    """Staff edit their own postings; admins edit everything, including ownerless ones."""
    return bool(user) and (user.get("admin") or item.get("owner") == user["email"])

def visible_to(user, items):
    return items if user.get("admin") else [i for i in items if i.get("owner") == user["email"]]

# ---------- http ----------

STATIC = {"/": "index.html", "/admin": "admin.html", "/style.css": "style.css", "/listing.js": "listing.js"}

class Handler(BaseHTTPRequestHandler):
    server_version = "careers"

    def send(self, code, payload=None, cookie=None):
        body = b"" if payload is None else json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(body)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n < 0 or n > 100_000:
            raise ValueError("Request too large.")
        body = json.loads(self.rfile.read(n) or b"{}")
        if not isinstance(body, dict):
            raise ValueError("Expected a JSON object.")
        return body

    def client_ip(self):
        # Behind Caddy/nginx the socket address is the proxy, so trust its forwarded header.
        fwd = self.headers.get("X-Forwarded-For")
        return fwd.split(",")[0].strip() if fwd else self.client_address[0]

    def do_GET(self):
        path = urlparse(self.path).path
        if path in STATIC:
            name = STATIC[path]
            with open(os.path.join(HERE, "static", name), "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/css" if name.endswith(".css") else "text/javascript; charset=utf-8" if name.endswith(".js") else "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif path == "/api/internships":
            self.send(200, public(load()))
        elif path == "/api/admin/internships":
            user = whoami(self)
            self.send(200, visible_to(user, load())) if user else self.send(401, {"error": "Please sign in."})
        elif path == "/api/config":
            contact = os.environ.get("MAINTAINER_EMAIL") or next((e for e, u in users().items() if u.get("admin")), "")
            self.send(200, {"today": board_today(), "maintainer_email": contact})
        elif path == "/api/session":
            user = whoami(self)
            self.send(200, {"authed": bool(user), "name": user["name"] if user else "",
                            "admin": bool(user and user.get("admin"))})
        else:
            self.send(404, {"error": "Not found."})

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            if path == "/api/login":
                b = self.body()
                email = str(b.get("email", "")).strip().lower()
                if not check_password(email, str(b.get("password", "")), self.client_ip()):
                    return self.send(401, {"error": "Wrong email or password."})
                tok = secrets.token_urlsafe(32)
                sessions[tok] = (email, time.time() + SESSION_HOURS * 3600)
                flags = "; Secure" if SECURE_COOKIE else ""
                return self.send(200, {"ok": True},
                                 f"sid={tok}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_HOURS*3600}{flags}")
            if path == "/api/logout":
                tok = http.cookies.SimpleCookie(self.headers.get("Cookie", "")).get("sid")
                sessions.pop(tok.value, None) if tok else None
                return self.send(200, {"ok": True}, "sid=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0")
            if path == "/api/internships":
                user = whoami(self)
                if not user:
                    return self.send(401, {"error": "Please sign in."})
                item = clean(self.body())
                item["id"] = secrets.token_hex(6)
                item["owner"] = user["email"]
                with lock:
                    items = load()
                    items.append(item)
                    save(items)
                return self.send(201, item)
            self.send(404, {"error": "Not found."})
        except (ValueError, json.JSONDecodeError) as e:
            self.send(400, {"error": str(e)})

    def edit(self, changer):
        """Shared owner check for PUT and DELETE."""
        path = urlparse(self.path).path
        if not path.startswith("/api/internships/"):
            return self.send(404, {"error": "Not found."})
        user = whoami(self)
        if not user:
            return self.send(401, {"error": "Please sign in."})
        iid = path.rsplit("/", 1)[1]
        with lock:
            items = load()
            for i in items:
                if i["id"] == iid:
                    if not may_edit(user, i):
                        return self.send(403, {"error": "That posting belongs to someone else."})
                    result = changer(i, items)
                    save(items)
                    return self.send(200, result)
        self.send(404, {"error": "No such opportunity."})

    def do_PUT(self):
        try:
            patch = clean(self.body())
        except (ValueError, json.JSONDecodeError) as e:
            return self.send(400, {"error": str(e)})
        self.edit(lambda item, items: item.update(patch) or item)

    def do_DELETE(self):
        self.edit(lambda item, items: items.remove(item) or {"ok": True})

    def log_message(self, fmt, *args):
        print(f"{self.command} {self.path} -> {args[1]}")

# ---------- account CLI ----------

def prompt_password():
    import getpass
    pw = getpass.getpass("Password: ")
    if len(pw) < 12:
        sys.exit("Use at least 12 characters.")
    if pw != getpass.getpass("Confirm: "):
        sys.exit("Passwords did not match.")
    return ph.hash(pw)

def cli(cmd, args):
    u = users()
    email = args[0].strip().lower() if args else ""
    if cmd == "users":
        if not u:
            return print("No accounts yet. Create one: server.py adduser <email>")
        for e, rec in sorted(u.items()):
            print(f"  {e:40} {rec.get('name', ''):28} {'admin' if rec.get('admin') else ''}")
    elif cmd == "adduser":
        if not email:
            sys.exit("Usage: server.py adduser <email>")
        if email in u:
            sys.exit(f"{email} already exists. Use: server.py passwd {email}")
        name = input("Full name (e.g. Dr. A. Rao): ").strip()
        admin = input("Admin — can see and edit everyone's postings? [y/N]: ").strip().lower() == "y"
        u[email] = {"hash": prompt_password(), "name": name or email, "admin": admin}
        save_users(u)
        print(f"Created {email}{' (admin)' if admin else ''}")
    elif cmd == "passwd":
        if email not in u:
            sys.exit(f"No account for {email}. See: server.py users")
        u[email]["hash"] = prompt_password()
        save_users(u)
        print(f"Password reset for {email}. Tell them to sign in again.")
    elif cmd == "deluser":
        if email not in u:
            sys.exit(f"No account for {email}.")
        if input(f"Delete {email}? Their postings stay and become admin-only. [y/N]: ").lower() != "y":
            sys.exit("Cancelled.")
        del u[email]
        save_users(u)
        print(f"Deleted {email}")
    else:
        sys.exit(__doc__)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cli(sys.argv[1], sys.argv[2:])
    else:
        if not users():
            print("No accounts yet — run: server.py adduser <email>")
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
        except OSError:
            sys.exit(f"Port {PORT} is already in use. Stop the other server, or run: PORT=8001 server.py")
        print(f"http://localhost:{PORT}  (staff sign-in: /admin)")
        srv.serve_forever()
