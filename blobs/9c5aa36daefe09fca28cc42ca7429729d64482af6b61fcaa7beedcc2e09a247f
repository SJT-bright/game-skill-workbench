#!/usr/bin/env python3
"""Cocos 3.x strict host server: serves one unzipped TikTok package plus the host files.

Binds 127.0.0.1 only. Usage: server.py PORT PACKAGE_DIR LOG_FILE (same as ../../ad_regression/server.py)
/                 -> the unzipped upload package, served unchanged
/__host/...       -> host.js, play.html
/__host/sizes.json -> {subpackage name: bytes under its root}, so bps throttling uses real sizes
POST /__log       -> appends JSON lines to LOG_FILE; every GET of a package file is logged as
                     {"kind": "http-get"} (network suite, make_runtime_resource_manifest.py)
Source: LunasJade QA host server (D3), merged with the 2.x host server's logging.
"""
import functools
import http.server
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
HOST_FILES = {'/__host/host.js', '/__host/play.html'}
LOG = os.devnull
PACKAGE = None


def subpackage_sizes(package):
    try:
        with open(os.path.join(package, 'game.json'), encoding='utf-8') as f:
            game = json.load(f)
    except (OSError, ValueError):
        return {}
    sizes = {}
    for sub in game.get('subpackages') or game.get('subPackages') or []:
        name, root = sub.get('name'), (sub.get('root') or '').strip('/')
        if not name or not root:
            continue
        total = 0
        for folder, _dirs, files in os.walk(os.path.join(package, root)):
            total += sum(os.path.getsize(os.path.join(folder, n)) for n in files)
        sizes[name] = total
    return sizes


class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        p = path.split('?', 1)[0].split('#', 1)[0]
        if p in HOST_FILES:
            return os.path.join(ROOT, p[len('/__host/'):])
        if p == '/':
            return os.path.join(ROOT, 'play.html')
        return super().translate_path(path)

    def do_GET(self):
        if self.path.split('?', 1)[0] == '/__host/sizes.json':
            body = json.dumps(subpackage_sizes(PACKAGE)).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def do_POST(self):
        if self.path.startswith('/__log'):
            n = int(self.headers.get('Content-Length') or 0)
            body = self.rfile.read(n).decode('utf-8', 'replace')
            with open(LOG, 'a', encoding='utf-8') as f:
                f.write(body.replace('\n', ' ') + '\n')
            self.send_response(204)
            self.end_headers()
            return
        self.send_response(404)
        self.end_headers()

    def log_request(self, code='-', size='-'):
        if self.command not in ('GET', 'HEAD'):
            return
        p = self.path.split('?', 1)[0].split('#', 1)[0]
        if p.startswith('/__host/') or p == '/':
            return
        try:
            status = int(code)
        except (TypeError, ValueError):
            status = str(code)
        row = {'kind': 'http-get', 'data': {'path': p, 'status': status, 'method': self.command}}
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(json.dumps(row) + '\n')

    def log_message(self, *args):
        pass


Handler.extensions_map.update({'.wasm': 'application/wasm', '.js': 'text/javascript',
                               '.json': 'application/json'})

if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise SystemExit('usage: server.py PORT PACKAGE_DIR LOG_FILE')
    port, PACKAGE, LOG = int(sys.argv[1]), os.path.abspath(sys.argv[2]), os.path.abspath(sys.argv[3])
    handler = functools.partial(Handler, directory=PACKAGE)
    http.server.ThreadingHTTPServer(('127.0.0.1', port), handler).serve_forever()
