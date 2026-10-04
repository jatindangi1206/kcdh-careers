"""Shared-store check: .venv/bin/python test_shared_store.py (requires redis-server/redis-cli)."""
import http.client, json, os, subprocess, tempfile, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import server

with tempfile.TemporaryDirectory() as tmp:
    sock = os.path.join(tmp, 'redis.sock')
    process = subprocess.Popen(['redis-server', '--port', '0', '--unixsocket', sock,
                                '--save', '', '--appendonly', 'no', '--dir', tmp],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    proxy = app = None
    try:
        for _ in range(100):
            if os.path.exists(sock):
                break
            time.sleep(.02)
        assert os.path.exists(sock), 'test Redis did not start'
        class REST(BaseHTTPRequestHandler):
            def do_POST(self):
                assert self.headers['Authorization'] == 'Bearer test-only'
                command = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                result = subprocess.check_output(['redis-cli', '-s', sock, '--json', *map(str, command)], text=True)
                body = json.dumps({'result': json.loads(result)}).encode()
                self.send_response(200); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
            def log_message(self, *args):
                pass
        proxy = ThreadingHTTPServer(('127.0.0.1', 0), REST)
        threading.Thread(target=proxy.serve_forever, daemon=True).start()
        server.REMOTE = True
        server.REDIS_URL = f'http://127.0.0.1:{proxy.server_port}'
        server.REDIS_TOKEN = 'test-only'
        assert server.load() == [] and server.users() == {}
        password = 'temporary test password'
        account = {'hash': server.ph.hash(password), 'admin': True, 'name': 'Test admin'}
        server.save_users({'admin@example.edu': account})
        server.save([{'id': 'original', 'deadline': '2030-01-01'}])
        stale = server.load()
        def other_worker():
            items = server.load(); items.append({'id': 'other', 'deadline': '2030-01-01'}); server.save(items)
        worker = threading.Thread(target=other_worker); worker.start(); worker.join()
        try:
            server.save(stale)
            assert False, 'stale worker overwrote another update'
        except server.StoreError as error:
            assert error.status == 409
        assert len(server.load()) == 2
        server.set_session('token', 'admin@example.edu')
        server.sessions.clear()
        assert server.get_session('token')[0] == 'admin@example.edu'
        assert server.redis('TTL', server.PREFIX + 'session:token') > 0
        server.delete_session('token'); assert server.get_session('token') is None
        for _ in range(10):
            assert not server.check_password('admin@example.edu', 'wrong', 'test-ip')
        assert not server.check_password('admin@example.edu', password, 'test-ip')
        key = server.PREFIX + 'fails:' + server.hashlib.sha256(b'test-ip').hexdigest()
        assert 0 < server.redis('TTL', key) <= 300
        server.redis('DEL', key)
        assert server.check_password('admin@example.edu', password, 'test-ip')
        app = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        threading.Thread(target=app.serve_forever, daemon=True).start()
        def request(method, path, data=None, cookie=''):
            conn = http.client.HTTPConnection('127.0.0.1', app.server_port)
            conn.request(method, path, json.dumps(data) if data else None, {'Cookie': cookie})
            response = conn.getresponse(); result = response.status, dict(response.getheaders()), json.loads(response.read()); conn.close(); return result
        code, headers, _ = request('POST', '/api/login', {'email':'admin@example.edu', 'password':password})
        assert code == 200
        cookie = headers['Set-Cookie'].split(';')[0]
        server.sessions.clear()
        assert request('GET', '/api/session', cookie=cookie)[2]['authed']
        posting = {'title':'Remote job', 'deadline':'2030-01-01', 'posting_type':'job', 'apply_url':'https://example.edu/apply'}
        assert request('POST', '/api/internships', posting, cookie)[0] == 201
        assert len(request('GET', '/api/internships')[2]) == 3
        server.REDIS_TOKEN = ''
        assert request('GET', '/api/internships')[0] == 503
        # Vercel invokes do_GET without BaseHTTPRequestHandler.handle_one_request.
        probe = server.Handler.__new__(server.Handler)
        probe.path = '/api/internships'
        responses = []
        probe.send = lambda code, payload: responses.append((code, payload))
        probe.do_GET()
        assert responses[0][0] == 503
        print('shared store ok')
    finally:
        for httpd in (app, proxy):
            if httpd:
                httpd.shutdown(); httpd.server_close()
        process.terminate(); process.wait(timeout=5)
