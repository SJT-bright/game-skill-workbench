#!/usr/bin/env python3
"""Bootstrap state names (never approve archived pixels), or assemble the reusable portion of a new round."""
import argparse
import json
from pathlib import Path
import re
import shutil
import tempfile

from art_round_check import run


def bootstrap(dumps, output):
    cases = []
    ids = set()
    for f in sorted(dumps.rglob('*ui-dump-*.json')):
        d = json.loads(f.read_text(encoding='utf-8'))
        screen = d['screen']
        viewport = d['viewport']
        identifier = d.get('capture_name') or f.stem.split('ui-dump-', 1)[1]
        if not re.fullmatch(r'[A-Za-z0-9_-][A-Za-z0-9._-]*', identifier) or identifier in ids:
            raise ValueError('ambiguous state id: ' + identifier)
        ids.add(identifier)
        cases.append(dict(id=identifier, screen=screen, kind=d['kind'], width=viewport['width'], height=viewport['height'],
                          dpr=(d.get('page') or {}).get('dpr') or d.get('plan_dpr'), stable=False,
                          recipe='', environment='', witness=[]))
    if not cases:
        raise ValueError('no captured states; list the actual screen/state and viewport cases first')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as out:
        json.dump({'cases': cases}, out, ensure_ascii=False, indent=2)


def assemble(project, build, dumps, output):
    if output.exists() or output.resolve().is_relative_to(dumps.resolve()):
        raise ValueError('new capture directory must be unused and outside the old capture directory')
    report = run('plan', project, build, dumps)
    if 'error' in report:
        raise ValueError(report['error'])
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        stage = Path(tmp)/'next'
        stage.mkdir()
        for case in report['cases']:
            if case['action'] in ('reuse','fresh'):
                for filename in (case['id']+'.png', 'capture-ui-dump-'+case['id']+'.json'):
                    shutil.copyfile(dumps/filename, stage/filename)
        stage.rename(output)
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init')
    init.add_argument('dumps', type=Path)
    init.add_argument('output', type=Path)
    prepare = sub.add_parser('assemble')
    for name in ('project', 'build', 'dumps', 'output'):
        prepare.add_argument(name, type=Path)
    a = ap.parse_args()
    try:
        if a.command == 'init':
            bootstrap(a.dumps, a.output)
        else:
            print(json.dumps(assemble(a.project, a.build, a.dumps, a.output), ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        ap.exit(1, str(exc)+'\n')


if __name__ == '__main__':
    main()
