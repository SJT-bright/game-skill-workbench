#!/usr/bin/env python3
"""Turn the strict host's load log into a runtime resource manifest (D7 item 14, D3 problem 5).

Some games load resources through paths built at runtime (Germ2048 v3: `r.load` escapes the static call
inventory), and Cocos 3.x SystemJS games are not expanded by audit_runtime_resources.py at all. For them
the manifest comes from what the REAL package requested while it ran in the strict host:

  python3 -B runtime_regression.py run --package <unpacked> --adapter <adapter.json> --suites network --work <dir>
  python3 -B make_runtime_resource_manifest.py --native <unpacked> --log <dir>/network/host-log.jsonl \\
      [--log <dir>/startup/host-log.jsonl ...] --out <manifest.json>

Every `{"kind": "http-get"}` row the host server wrote (ad_regression/server.py, runtime_regression/host3x/
server.py) must name a file inside the package that was served with status 200. A request for a file the
package does not contain is a refusal (that is a missing resource on the phone), never a skip. Requests that
are not package files are listed under "excluded" with the reason: the browser's /favicon.ico, the host's
blocked-network sink and the in-memory USER_DATA_PATH (ttfile://). The manifest binds the exact package bytes
(per-file sha256 and a tree digest), so it cannot be reused for another build.

Schema runtime_resource_manifest.observed.v1; build_checked_zip.py --resource-manifest accepts it through
audit_runtime_resources.audit(), only for packages the static expansion cannot read. Not a phone pass.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
from urllib.parse import unquote

SCHEMA = 'runtime_resource_manifest.observed.v1'
NOT_PACKAGE = (
    ('/favicon.ico', 'browser favicon probe, not a game request'),
    ('/__net_blocked', 'external request blocked by the strict host (see the network suite)'),
)


class ManifestRefused(ValueError):
    """The observed requests do not match the package; no manifest is written."""


def tree_digest(files):
    h = hashlib.sha256()
    for name in sorted(files):
        h.update(name.encode('utf-8') + b'\0' + hashlib.sha256(files[name]).hexdigest().encode() + b'\n')
    return h.hexdigest()


def package_files(native):
    root = Path(native)
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob('*')) if p.is_file()}


def read_rows(log_path):
    rows = []
    for number, line in enumerate(Path(log_path).read_text(encoding='utf-8').splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue  # a page beacon cut by the browser; http-get rows are written whole by the server
        if isinstance(row, dict) and row.get('kind') == 'http-get' and isinstance(row.get('data'), dict):
            rows.append((number, row['data']))
    return rows


def classify(url_path):
    """Return (package relative path or None, exclusion reason or None)."""
    p = unquote(str(url_path)).split('?', 1)[0].split('#', 1)[0]
    for prefix, reason in NOT_PACKAGE:
        if p == prefix or p.startswith(prefix + '/'):
            return None, reason
    rel = p.lstrip('/')
    if rel.startswith('ttfile:'):
        return None, 'host in-memory USER_DATA_PATH (tt.env.USER_DATA_PATH), not a package file'
    parts = PurePosixPath(rel).parts
    if not rel or '..' in parts:
        return None, None
    return rel, None


def build(native, logs):
    files = package_files(native)
    if 'game.js' not in files:
        raise ManifestRefused('no game.js at package root: ' + str(native))
    if not logs:
        raise ManifestRefused('at least one --log (host-log.jsonl from runtime_regression.py --work) is required')
    observed, excluded, problems, log_meta = {}, {}, [], []
    for log in logs:
        log = Path(log)
        try:
            rows = read_rows(log)
        except OSError as error:
            raise ManifestRefused('cannot read log %s: %s' % (log, error))
        log_meta.append({'path': str(log.resolve()), 'sha256': hashlib.sha256(log.read_bytes()).hexdigest(),
                         'http_get_rows': len(rows)})
        for number, data in rows:
            rel, reason = classify(data.get('path'))
            if reason:
                excluded.setdefault(str(data.get('path')), reason)
                continue
            if rel is None:
                problems.append('%s:%d unusable request path %r' % (log.name, number, data.get('path')))
                continue
            if rel not in files:
                problems.append('%s:%d request not in the package: /%s (status %s)' % (log.name, number, rel, data.get('status')))
                continue
            if data.get('status') != 200:
                problems.append('%s:%d package file served with status %s: /%s' % (log.name, number, data.get('status'), rel))
                continue
            observed[rel] = observed.get(rel, 0) + 1
    if not observed:
        problems.append('the logs contain no package file request: run the package in the strict host first')
    elif 'game.js' not in observed:
        problems.append('game.js was never requested: the logs are not from a boot of this package')
    if problems:
        raise ManifestRefused('; '.join(problems[:20]) + (' (+%d more)' % (len(problems) - 20) if len(problems) > 20 else ''))
    return {
        'schema': SCHEMA,
        'about': 'files the package requested in the strict TikTok host (startup, home, one level); not a phone pass',
        'package_tree_sha256': tree_digest(files),
        'package_files': len(files),
        'observed_files': [{'path': rel, 'sha256': hashlib.sha256(files[rel]).hexdigest(), 'bytes': len(files[rel]),
                            'requests': observed[rel]} for rel in sorted(observed)],
        'excluded': [{'path': p, 'reason': r} for p, r in sorted(excluded.items())],
        'logs': log_meta,
        'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }


def verify(files, manifest):
    """Check an observed manifest against package bytes (for audit_runtime_resources / prepare_delivery)."""
    if not isinstance(manifest, dict) or manifest.get('schema') != SCHEMA:
        raise ManifestRefused('not a %s manifest' % SCHEMA)
    if manifest.get('package_tree_sha256') != tree_digest(files):
        raise ManifestRefused('observed resource manifest was made for different package bytes')
    rows = manifest.get('observed_files')
    if not isinstance(rows, list) or not rows:
        raise ManifestRefused('observed resource manifest lists no files')
    for row in rows:
        name = row.get('path') if isinstance(row, dict) else None
        if name not in files or hashlib.sha256(files[name]).hexdigest() != row.get('sha256'):
            raise ManifestRefused('observed resource missing or changed in the package: %r' % (name,))
    if 'game.js' not in {r['path'] for r in rows}:
        raise ManifestRefused('observed resource manifest does not include game.js')
    return {'passed': True, 'schema': SCHEMA, 'observed_files': len(rows), 'package_files': len(files)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--native', type=Path, required=True, help='unpacked TikTok package (the bytes that will ship)')
    ap.add_argument('--log', type=Path, action='append', default=[], help='host-log.jsonl (repeatable)')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(argv)
    try:
        if a.out.exists():
            raise ManifestRefused('manifest output already exists')
        if a.out.resolve().is_relative_to(a.native.resolve()):
            raise ManifestRefused('resource manifest must stay outside the upload tree')
        manifest = build(a.native, a.log)
        a.out.parent.mkdir(parents=True, exist_ok=True)
        with a.out.open('x', encoding='utf-8') as stream:
            json.dump(manifest, stream, ensure_ascii=False, indent=2)
        print(json.dumps({'status': 'runtime_resource_manifest_written', 'observed_files': len(manifest['observed_files']),
                          'excluded': len(manifest['excluded']), 'out': str(a.out)}, ensure_ascii=False))
        return 0
    except (ManifestRefused, OSError) as error:
        print(json.dumps({'status': 'refuse', 'error': str(error)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    sys.exit(main())
