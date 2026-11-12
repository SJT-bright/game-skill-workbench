#!/usr/bin/env python3
"""Explicit modal lifecycle check using the unchanged shared runner and scope gates."""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'scripts'))
import runtime_regression as runtime


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True, help='actual unpacked Native directory')
    parser.add_argument('--adapter', type=Path, required=True, help='project-specific modal adapter, separate from ad adapter')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--work', type=Path)
    args = parser.parse_args()
    try:
        result = runtime.run(args.package, args.adapter, ['modal_lifecycle'], work=args.work, suites_dir=HERE)
        code = 0 if result.get('passed') is True else 1
    except (runtime.RuntimeRefused, ValueError, OSError) as error:
        result = getattr(error, 'summary', None) or {'passed': False, 'status': 'refused'}
        result['error'] = str(error)
        code = 1
    result['acceptance_scope'] = 'Explicit modal lifecycle only; not full game, platform, or physical-device acceptance'
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({'passed': result.get('passed'), 'scope': result['acceptance_scope'],
                      'report': str(args.out), 'error': result.get('error')}, ensure_ascii=False))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
