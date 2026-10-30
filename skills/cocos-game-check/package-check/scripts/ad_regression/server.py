#!/usr/bin/env python3
"""Ad-regression host server: serves one unzipped TikTok package plus the host files.

Binds 127.0.0.1 only. Usage: server.py PORT PACKAGE_DIR LOG_FILE
POST /__log appends JSON lines to LOG_FILE.
"""
import functools
import http.server
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
HOST_FILES = {'/__host/host.js', '/__host/play.html'}
LOG = os.devnull


class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        p = path.split('?', 1)[0].split('#', 1)[0]
        if p in HOST_FILES:
            return os.path.join(ROOT, p[len('/__host/'):])
        if p == '/':
            return os.path.join(ROOT, 'play.html')
        return super().translate_path(path)

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
        # Every package file the page fetched, with its status: the runtime resource manifest
        # (make_runtime_resource_manifest.py) and the network suite read these rows.
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


Handler.extensions_map.update({'.wasm': 'application/wasm', '.js': 'application/javascript',
                               '.json': 'application/json'})

if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise SystemExit('usage: server.py PORT PACKAGE_DIR LOG_FILE')
    port, package, LOG = int(sys.argv[1]), os.path.abspath(sys.argv[2]), os.path.abspath(sys.argv[3])
    handler = functools.partial(Handler, directory=package)
    http.server.ThreadingHTTPServer(('127.0.0.1', port), handler).serve_forever()
