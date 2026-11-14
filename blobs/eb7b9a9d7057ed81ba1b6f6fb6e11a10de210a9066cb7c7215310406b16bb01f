"""Known retired production advice, checked only during Skill maintenance.

This is a bounded registry, not a general semantic proof or a game gate.
Explicit source paths prevent historical fixtures and compatibility code from
being interpreted as active instructions. Precedence banners never hide a hit.
"""
import argparse
import json
from pathlib import Path
import re

POLICY = Path(__file__).resolve().parents[1] / 'assets/active-skill-advice.json'


def load_policy(path=POLICY):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if data.get('schema') != 'active_skill_advice.v1' or not isinstance(data.get('rules'), list) or not data['rules']:
        raise ValueError('invalid active Skill advice registry')
    ids = set()
    for rule in data['rules']:
        if not isinstance(rule, dict) or not isinstance(rule.get('id'), str) or rule['id'] in ids:
            raise ValueError('invalid or duplicate retired advice ID')
        ids.add(rule['id'])
        if not rule.get('current') or not rule.get('matches') or not rule.get('stale_control'):
            raise ValueError('retired advice requires current source, match scope and a counterexample')
        for match in rule['matches']:
            if not isinstance(match, dict) or not match.get('paths') or not isinstance(match.get('pattern'), str):
                raise ValueError('invalid scoped advice matcher')
            re.compile(match['pattern'])
            for relative in match['paths']:
                path = Path(relative)
                if path.is_absolute() or '..' in path.parts:
                    raise ValueError('advice path must be relative')
    return data


def scan(root, policy=None):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError('Skill tree missing')
    policy = load_policy() if policy is None else policy
    findings = []
    for rule in policy['rules']:
        for matcher in rule['matches']:
            rx = re.compile(matcher['pattern'])
            for relative in matcher['paths']:
                path = root / relative
                if not path.exists():
                    continue  # A partial fixture or a pack without this optional module.
                if path.is_symlink() or not path.resolve().is_relative_to(root):
                    raise ValueError('advice source escapes Skill tree: ' + relative)
                for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                    if rx.search(line):
                        findings.append(dict(id=rule['id'], file=relative, line=number,
                                             text=line, current=rule['current']))
    return findings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    args = parser.parse_args(argv)
    try:
        findings = scan(args.root)
        result = dict(schema='active_skill_advice_report.v1', passed=not findings,
                      findings=findings, boundary='Known maintenance rules only; no game execution')
    except (OSError, ValueError, TypeError, KeyError, re.error) as error:
        result = dict(schema='active_skill_advice_report.v1', passed=False, status='not_run', error=str(error))
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
