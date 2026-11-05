#!/usr/bin/env python3
"""Startup size ledger docs/startup/budget.json (生成时预防 P04). Shared by every step that writes a file into a game.

Why: in the 2026-11-04 census 39 games (46 times) had a package or first download that was too big and 34 games
(42 times) got stuck at startup; it was only seen when the package was written (upload_size_gate.py,
verify_native_zip.py). Here every file that lands in the project is added to a ledger with its bytes and whether it
is in the first download (the main package plus any subpackage requested before the home page). When the estimate
of the first download goes over 10 MiB the step that added the file stops right away, before any build.

The ledger is seeded by first_screen.py when work starts (one row per file of the first download). Writers then
call record(); a call that would push the estimate over the limit raises BudgetError and writes nothing:

    import startup_budget
    startup_budget.record(project, 'assets/home/bg.png', source='postprocess')            # bytes read from disk
    startup_budget.record(project, 'assets/resources/audio/bgm.mp3', need='deferred', source='import_audio')

  python3 -B startup_budget.py --project <p> show               # print the estimate
  python3 -B startup_budget.py --project <p> add --file <f> [--home|--deferred] [--bytes N] [--source NAME]
  python3 -B startup_budget.py --project <p> refresh            # re-run first_screen.py and rebuild the ledger

The estimate uses audit_package_estimate.py's numbers (engine allowance by engine major, scenes/prefabs counted at
SERIALIZED_FACTOR) and adds the bytedance build template; it is a source estimate, not the real package: the native
ZIP check stays the final gate. No machine paths, no platform-specific commands.
Exit: 0 within budget, 1 over budget / refused, 2 bad input.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import audit_package_estimate as estimate  # noqa: E402  same allowance and serialized factor as the source estimate

SCHEMA = 'startup_budget.v1'
LEDGER = ('docs', 'startup', 'budget.json')
LIMIT = 10 * 1024 * 1024          # package_gates/startup.py + runtime layout_state: 10 MiB before the home page
AUDIO = ('.mp3', '.ogg', '.wav', '.m4a', '.aac')


class BudgetError(Exception):
    """The file would push the first download over the limit (or the ledger is unusable)."""


def ledger_path(project: Path) -> Path:
    return Path(project).joinpath(*LEDGER)


def counted_bytes(path: Path, size: int | None = None) -> int:
    size = path.stat().st_size if size is None else int(size)
    return int(size * estimate.SERIALIZED_FACTOR) if path.suffix in estimate.SERIALIZED else size


def fixed_bytes(project: Path) -> dict:
    _, major = estimate.engine_major(project)
    tpl = project / 'build-templates' / 'bytedance'
    template = sum(p.stat().st_size for p in estimate.files(tpl)) if tpl.is_dir() else 0
    return {'engine_allowance_bytes': estimate.ENGINE_ALLOWANCE[major], 'bytedance_template_bytes': template}


def summarize(data: dict) -> dict:
    rows = data.get('files') or {}
    home = sum(r['bytes'] for r in rows.values() if r.get('first_download'))
    fixed = data.get('fixed') or {}
    total = home + int(fixed.get('engine_allowance_bytes', 0)) + int(fixed.get('bytedance_template_bytes', 0))
    audio = sorted(f for f, r in rows.items() if r.get('first_download') and f.lower().endswith(AUDIO))
    return {'first_download_bytes': total, 'limit_bytes': data.get('limit_bytes', LIMIT),
            'over': total > data.get('limit_bytes', LIMIT), 'files_in_first_download': sum(
                1 for r in rows.values() if r.get('first_download')), 'audio_in_first_download': audio}


def load(project) -> dict:
    project = Path(project)
    p = ledger_path(project)
    if p.is_file():
        try:
            data = json.loads(p.read_text(encoding='utf-8'))
        except ValueError as exc:
            raise BudgetError('%s is not valid JSON: %s' % (p, exc))
        if data.get('schema') != SCHEMA:
            raise BudgetError('%s has schema %r, expected %s' % (p, data.get('schema'), SCHEMA))
        return data
    return seed(project)


def seed(project) -> dict:
    """No ledger yet: build it from first_screen.py's analysis (it writes docs/startup/first-screen.json too)."""
    import first_screen
    try:
        report = first_screen.analyze(Path(project))
    except ValueError as exc:            # no scene yet (a bare new project): start an empty ledger, say why
        bset = estimate.bundles(Path(project))
        data = new_ledger(project, {}, {'subpackage_bundles': sorted(b for b, t in bset.items() if t == 'subpackage'),
                                        'main_bundles': sorted(b for b, t in bset.items() if t != 'subpackage'),
                                        'pre_home_bundles': []})
        data['note'] = 'seeded without first_screen.py (%s); run it when the scenes exist' % exc
        return data
    first_screen.write(Path(project), report)
    return json.loads(ledger_path(Path(project)).read_text(encoding='utf-8'))


def save(project, data: dict) -> Path:
    p = ledger_path(Path(project))
    p.parent.mkdir(parents=True, exist_ok=True)
    data['summary'] = summarize(data)
    data['updated_at'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
    tmp = p.with_name(p.name + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    os.replace(tmp, p)
    return p


def new_ledger(project, rows: dict, groups: dict) -> dict:
    return {'schema': SCHEMA, 'tool': 'startup_budget', 'limit_bytes': LIMIT, 'fixed': fixed_bytes(Path(project)),
            'groups': groups, 'files': rows}


def in_first_download(data: dict, rel: str) -> bool:
    """Where a new file lands decides whether players download it before the home page."""
    g = data.get('groups') or {}
    sub = g.get('subpackage_bundles') or []
    early = set(g.get('pre_home_bundles') or [])
    rel = rel[len('assets/'):] if rel.startswith('assets/') else rel
    owner = None
    for b in sub + list(g.get('main_bundles') or []):
        if (rel == b or rel.startswith(b + '/')) and (owner is None or len(b) > len(owner)):
            owner = b
    if owner is None or owner not in sub:
        return True               # main package (outside bundles, or a bundle that is not a ByteDance subpackage)
    return owner in early


def record(project, file, size: int | None = None, need: str = 'home', source: str = '', first_download=None,
           dry_run: bool = False) -> dict:
    """Add or replace one file's row. need: 'home' (the home page shows it) or 'deferred'. Raises BudgetError when the
    first download would go over the limit; nothing is written then."""
    project = Path(project)
    if need not in ('home', 'deferred'):
        raise BudgetError('need must be home or deferred, not %r' % need)
    path = Path(file)
    path = path if path.is_absolute() else project / path
    rel = path.resolve().relative_to(project.resolve()).as_posix()
    if size is None and not path.is_file():
        raise BudgetError('%s does not exist; pass its size' % file)
    data = load(project)
    first = in_first_download(data, rel) if first_download is None else bool(first_download)
    rows = dict(data.get('files') or {})
    rows[rel] = {'bytes': counted_bytes(path, size), 'need': need, 'first_download': first, 'source': source}
    trial = dict(data, files=rows)
    s = summarize(trial)
    if s['over']:
        raise BudgetError('%s (%d bytes, %s) would make the first download %.2f MiB > %.0f MiB: put it in a subpackage '
                          'bundle loaded after the home page (ResLoader), or shrink it' % (
                              rel, rows[rel]['bytes'], 'home page' if need == 'home' else 'deferred but in the main package',
                              s['first_download_bytes'] / 1048576.0, s['limit_bytes'] / 1048576.0))
    if not dry_run:
        save(project, trial)
    return {'file': rel, 'first_download': first, 'need': need, 'summary': s,
            'warning': ('sound in the first download: the startup contract wants sound in its own subpackage'
                        if first and rel.lower().endswith(AUDIO) else '')}


def record_many(project, items, source: str = '', dry_run: bool = False) -> dict:
    """items: [(file, size or None, need)]. All or nothing: BudgetError when the sum goes over the limit."""
    project = Path(project)
    data = load(project)
    rows = dict(data.get('files') or {})
    added, warnings = [], []
    for file, size, need in items:
        path = Path(file)
        path = path if path.is_absolute() else project / path
        rel = path.resolve().relative_to(project.resolve()).as_posix()
        first = in_first_download(data, rel)
        rows[rel] = {'bytes': counted_bytes(path, size), 'need': need, 'first_download': first, 'source': source}
        added.append(rel)
        if first and rel.lower().endswith(AUDIO):
            warnings.append('%s: sound in the first download; the startup contract wants sound in its own subpackage '
                            '(make the bundle holding it a ByteDance subpackage)' % rel)
    trial = dict(data, files=rows)
    s = summarize(trial)
    if s['over']:
        raise BudgetError('adding %s would make the first download %.2f MiB > %.0f MiB: put them in a subpackage bundle '
                          'loaded after the home page, or shrink them' % (', '.join(added), s['first_download_bytes'] /
                                                                          1048576.0, s['limit_bytes'] / 1048576.0))
    if not dry_run:
        save(project, trial)
    return {'files': added, 'summary': s, 'warnings': warnings}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('show')
    sub.add_parser('refresh')
    add = sub.add_parser('add')
    add.add_argument('--file', required=True)
    add.add_argument('--bytes', type=int)
    g = add.add_mutually_exclusive_group()
    g.add_argument('--home', action='store_true', help='the home page shows it (default)')
    g.add_argument('--deferred', action='store_true', help='used only after the home page')
    add.add_argument('--source', default='cli')
    a = ap.parse_args(argv)
    if not (a.project / 'assets').is_dir():
        print(json.dumps({'status': 'error', 'error': 'no assets folder in %s' % a.project}, ensure_ascii=False))
        return 2
    try:
        if a.cmd == 'refresh':
            import first_screen
            first_screen.write(a.project, first_screen.analyze(a.project))
            out = summarize(load(a.project))
        elif a.cmd == 'show':
            out = summarize(load(a.project))
        else:
            out = record(a.project, a.file, a.bytes, 'deferred' if a.deferred else 'home', a.source)
    except BudgetError as exc:
        print(json.dumps({'status': 'over_budget', 'error': str(exc)}, ensure_ascii=False))
        return 1
    over = (out.get('summary') or out).get('over')
    print(json.dumps({'status': 'over_budget' if over else 'ok', **out}, ensure_ascii=False))
    return 1 if over else 0


if __name__ == '__main__':
    sys.exit(main())
