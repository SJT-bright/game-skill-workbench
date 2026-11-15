#!/usr/bin/env python3
"""Prepare an isolated Cocos 2.4 UI maintenance fixture; never starts a browser/service/game."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil

KIT = Path(__file__).resolve().parents[2]
TEMPLATE = KIT / 'tests' / 'real-engine-ui'
PARTS = ('GameUIKit.js', 'ScreenFit.js')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(engine_bundle, candidate_kit, out, baseline_kit=None):
    engine = Path(engine_bundle).resolve()
    candidate = Path(candidate_kit).resolve()
    baseline = Path(baseline_kit).resolve() if baseline_kit else None
    target = Path(out).resolve()
    if target.exists():
        raise ValueError('output already exists; choose a new directory')
    if not engine.is_file():
        raise ValueError('engine bundle must be an existing file')
    for root in (KIT, candidate, baseline):
        if root and (target == root or root in target.parents):
            raise ValueError('output must be outside input kit trees')
    inputs = {'engine.js': engine, 'index.html': TEMPLATE / 'index.html', 'fixture.js': TEMPLATE / 'fixture.js'}
    for label, root in (('after', candidate), ('before', baseline)):
        if root is None:
            continue
        for name in PARTS:
            source = root / 'parts' / name
            if not source.is_file():
                raise ValueError('missing shared component: ' + str(source))
            inputs[label + '-' + name] = source
    report = {'schema': 'ui-real-engine-fixture.v1', 'mode': 'maintenance_only',
              'baseline_supplied': baseline is not None,
              'inputs': {name: {'path': str(source), 'sha256': digest(source)} for name, source in inputs.items()},
              'boundary': 'Cocos 2.4 browser component behavior only; not game/native/3.x/device/art acceptance',
              'starts_service_or_browser': False}
    target.mkdir(parents=True, exist_ok=False)
    for name, source in inputs.items():
        shutil.copyfile(source, target / name)
    (target / 'fixture-inputs.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--engine-bundle', type=Path, required=True)
    p.add_argument('--candidate-kit', type=Path, required=True)
    p.add_argument('--baseline-kit', type=Path)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(argv)
    try:
        result = prepare(a.engine_bundle, a.candidate_kit, a.out, a.baseline_kit)
    except (ValueError, OSError) as error:
        p.exit(2, 'prepare_ui_engine_fixture: ' + str(error) + '\n')
    print(json.dumps({'status': 'prepared', 'output': str(a.out.resolve()),
                      'input_count': len(result['inputs']), 'baseline_supplied': result['baseline_supplied']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
