"""One runnable check: .venv/bin/python test_server.py"""
import json, os, tempfile, server

# public() hides archived and past-deadline items, keeps today's
items = [
    {"id": "1", "title": "live", "deadline": "2030-01-01"},
    {"id": "2", "title": "today", "deadline": "2026-06-15"},
    {"id": "3", "title": "expired", "deadline": "2026-06-14"},
    {"id": "4", "title": "archived", "deadline": "2030-01-01", "archived": True},
]
assert [i["title"] for i in server.public(items, today="2026-06-15")] == ["live", "today"]

# clean() keeps known fields, drops junk, requires title + deadline
c = server.clean({"title": " Bio intern ", "deadline": "2030-01-01", "evil": "x", "archived": 1})
assert c["title"] == "Bio intern" and c["archived"] is True and "evil" not in c
for bad in ({"deadline": "2030-01-01"}, {"title": "x"}):
    try:
        server.clean(bad); assert False, "should have raised"
    except ValueError:
        pass

# clean() refuses a Google Form *editing* link, accepts the live one
try:
    server.clean({"title": "x", "deadline": "2030-01-01",
                  "apply_url": "https://docs.google.com/forms/d/ABC123/edit"})
    assert False, "edit link should be rejected"
except ValueError as e:
    assert "Send" in str(e)
server.clean({"title": "x", "deadline": "2030-01-01",
              "apply_url": "https://docs.google.com/forms/d/e/ABC123/viewform"})

# save/load round-trips
server.DATA = os.path.join(tempfile.mkdtemp(), "internships.json")
assert server.load() == []
server.save(items)
assert server.load() == items

# ownership: staff see and edit only their own; admin sees and edits everything
mine = {"id": "a", "owner": "rao@ashoka.edu.in"}
theirs = {"id": "b", "owner": "menon@ashoka.edu.in"}
orphan = {"id": "c"}
rao = {"email": "rao@ashoka.edu.in", "admin": False}
boss = {"email": "admin@ashoka.edu.in", "admin": True}
assert server.may_edit(rao, mine) and not server.may_edit(rao, theirs) and not server.may_edit(rao, orphan)
assert all(server.may_edit(boss, i) for i in (mine, theirs, orphan))
assert server.visible_to(rao, [mine, theirs, orphan]) == [mine]
assert server.visible_to(boss, [mine, theirs, orphan]) == [mine, theirs, orphan]

# passwords: right one passes, wrong one and unknown email fail, lockout after 10 tries
server.AUTH = os.path.join(tempfile.mkdtemp(), "auth.json")
server.save_users({"rao@ashoka.edu.in": {"hash": server.ph.hash("correct horse battery"),
                                         "name": "Prof. Rao", "admin": False}})
assert oct(os.stat(server.AUTH).st_mode)[-3:] == "600", "auth.json must not be world-readable"
assert server.check_password("rao@ashoka.edu.in", "correct horse battery", "1.1.1.1")
assert not server.check_password("rao@ashoka.edu.in", "wrong", "2.2.2.2")
assert not server.check_password("nobody@ashoka.edu.in", "correct horse battery", "2.2.2.2")
for _ in range(10):
    server.check_password("rao@ashoka.edu.in", "wrong", "3.3.3.3")
assert not server.check_password("rao@ashoka.edu.in", "correct horse battery", "3.3.3.3"), "lockout not enforced"

# New posting fields, strict validation, and old mailto postings.
base = {"title": "Research intern", "deadline": "2030-01-01", "application_method": "url",
        "apply_url": "https://forms.gle/example", "details": "First paragraph.\n\nSecond paragraph.",
        "document_title": "Project brief", "document_url": "https://example.edu/brief.pdf"}
assert server.clean(base)["details"] == base["details"]
assert server.clean(base)["posting_type"] == "internship"
assert server.clean(dict(base, posting_type="job"))["posting_type"] == "job"
mail = dict(base, posting_type="job", application_method="email", apply_email="rao@ashoka.edu.in", email_subject="Application: A & B")
assert server.clean(mail)["apply_url"] == ""
legacy = server.clean({"title": "Old", "deadline": "2030-01-01", "apply_url": "mailto:rao@ashoka.edu.in?subject=Research%20intern"})
assert legacy["application_method"] == "email" and legacy["email_subject"] == "Research intern"
for changes in ({"posting_type": "other"}, {"deadline": "2030-02-30"}, {"deadline": "20300101"},
                {"apply_url": "javascript:alert(1)"}, {"apply_url": "https://user:pass@example.com"},
                {"document_url": "data:text/html,bad"}, {"document_url": "", "document_title": "Brief"},
                {"application_method": "none"}, {"application_method": "unknown"},
                {"application_method": "email", "apply_email": "bad"},
                {"application_method": "email", "apply_email": "a@b.com", "email_subject": "A\nB"},
                {"title": None}):
    try:
        server.clean(dict(base, **changes))
        assert False, f"accepted invalid fields: {changes}"
    except ValueError:
        pass
assert server.clean(dict(base, application_method="none", archived=True))["archived"]
try:
    server.clean({"title": "Missing destination", "deadline": "2030-01-01"})
    assert False, "Published postings must have a destination even when the method is omitted"
except ValueError:
    pass
server.fails["old"] = (10, server.time.time() - 301)
assert not server.check_password("rao@ashoka.edu.in", "wrong", "old")
assert server.check_password("rao@ashoka.edu.in", "correct horse battery", "old")

# Real HTTP flow on an ephemeral port; all files/accounts are temporary.
import http.client, threading
account = server.users()["rao@ashoka.edu.in"]
server.save_users({"rao@ashoka.edu.in": account, "boss@ashoka.edu.in": dict(account, admin=True)})
server.save([])
httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
thread = threading.Thread(target=httpd.serve_forever, daemon=True)
thread.start()
def request(method, path, body=None, cookie=""):
    conn = http.client.HTTPConnection("127.0.0.1", httpd.server_port)
    conn.request(method, path, json.dumps(body) if body is not None else None,
                 {"Content-Type": "application/json", "Cookie": cookie})
    response = conn.getresponse()
    status, headers, data = response.status, dict(response.getheaders()), response.read()
    conn.close()
    return status, headers, json.loads(data) if headers.get("Content-Type") == "application/json" else data
try:
    assert request("GET", "/listing.js")[1]["Content-Type"].startswith("text/javascript")
    assert request("GET", "/api/config")[2]["today"] == server.board_today()
    assert request("POST", "/api/internships", base)[0] == 401
    code, headers, _ = request("POST", "/api/login", {"email": "RAO@ASHOKA.EDU.IN", "password": "correct horse battery"})
    assert code == 200
    cookie = headers["Set-Cookie"].split(";")[0]
    code, _, posting = request("POST", "/api/internships", mail, cookie)
    assert posting["posting_type"] == "job"
    assert code == 201 and posting["owner"] == "rao@ashoka.edu.in"
    assert request("GET", "/api/internships")[2][0]["email_subject"] == mail["email_subject"]
    path = "/api/internships/" + posting["id"]
    assert request("PUT", path, dict(base, deadline="invalid"), cookie)[0] == 400
    assert request("POST", "/api/internships", [], cookie)[0] == 400
    server.sessions["other"] = ("boss@ashoka.edu.in", server.time.time() + 60)
    # A second ordinary staff user cannot view or edit someone else's posting.
    server.save_users(dict(server.users(), **{"other@ashoka.edu.in": account}))
    server.sessions["staff"] = ("other@ashoka.edu.in", server.time.time() + 60)
    assert request("GET", "/api/admin/internships", cookie="sid=staff")[2] == []
    assert request("PUT", path, base, "sid=staff")[0] == 403
    assert request("DELETE", path, cookie="sid=staff")[0] == 403
    assert request("PUT", path, dict(mail, archived=True), cookie)[0] == 200
    assert request("GET", "/api/internships")[2] == []
    assert request("PUT", path, base, "sid=other")[0] == 200
    assert request("DELETE", path, cookie="sid=other")[0] == 200
    request("POST", "/api/logout", cookie=cookie)
    assert request("GET", "/api/session", cookie=cookie)[2]["authed"] is False
    assert request("PUT", path, base, cookie)[0] == 401
finally:
    httpd.shutdown(); httpd.server_close(); thread.join()
print("ok")
