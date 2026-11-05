#!/usr/bin/env python3
"""Economy capability record and hard-coded reward scan (P17 生成时预防, 2026-11-04).

One small record says what the game HAS before any number is made: an out-of-round wallet (main coin currency),
in-round items, skins, energy. make_economy_config.py writes it first (economy_capabilities.json, schema
remake-economy/references/economy_capabilities.schema.json); checks and diagnoses read the same file instead of guessing
each on their own (diagnose_misread: "B 定不出" on a no-coin game, x2 written as a score double).

Without a wallet there is no B. The replacements come from the rules table (never written here twice):
  result x2         ECON-NOCUR: doubles the items picked up this round, once a round; no items -> no x2 button
  add-to-desktop /  ECON-SHORTCUT / ECON-REVISIT params no_coin_with_energy (+3 energy once) or, with no energy either,
  home revisit      no_coin_no_energy = add_main_currency_and_skins (English: add a coin and skins while localizing,
                    then the normal 5B rows apply)

scan_hardcoded(root): a ~1 s scan of game scripts for reward numbers written into code (`coins += 30`,
`addCoins(50)`, `gold = gold + 20`); every reward must read economy_config.json. Platform kit / ad-boost vendor files,
library/temp/build and tests are skipped. Lines marked `// economy-ok` are skipped (a non-reward use you checked).

CLI:  python3 economy_capabilities.py scan --project <game> [--json]      exit 0 clean, 1 found, 2 bad input
      python3 economy_capabilities.py show --file economy_capabilities.json exit 0 valid, 2 invalid
"""
import argparse
import json
import re
import sys
from pathlib import Path

SCHEMA = 'economy_capabilities.v1'
KEYS = ('wallet', 'items', 'skins', 'energy')
PLANS = ('keep', 'add_main_currency_and_skins', 'none')

# reward-ish variable names; score / hp / level / index etc. are not money
_MONEY = r'(?:coins?|golds?|gems?|diamonds?|money|cash|stars?Coin|crystals?|jewels?|rubies|ruby|currency|wallet|balance)'
HARDCODED = [
    re.compile(r'(?i)\b(?:\w+\.)*(?P<name>\w*' + _MONEY + r')\s*(?P<op>\+=)\s*(?P<num>\d+(?:\.\d+)?)\b'),
    re.compile(r'(?i)\b(?:\w+\.)*(?P<name>\w*' + _MONEY + r')\s*=\s*(?:\w+\.)*(?P=name)\s*\+\s*(?P<num>\d+(?:\.\d+)?)\b'),
    re.compile(r'(?i)\b(?P<name>(?:add|give|grant|reward|award|earn|gain)\w*' + _MONEY + r'\w*)\s*\(\s*(?P<num>\d+(?:\.\d+)?)\s*[,)]'),
]
SCRIPT_SUFFIXES = ('.ts', '.js')
SKIP_PARTS = {'library', 'temp', 'build', 'node_modules', 'local', 'settings', 'platform-kit', 'vendor', 'tiktok-kit',
              '.tiktok-kit', 'tests', 'test', '__tests__'}
SKIP_NAMES = ('RewardedService', 'SaveStore', 'AdBoostKit', 'HomeGrowthEntries', 'MissionFlow')
ALLOW_MARK = 'economy-ok'


def make(wallet, items, skins, energy, kind='remake', wallet_currency=None, wallet_plan=None, evidence=None,
         rules_revision=None, written_by='make_economy_config.py'):
    if wallet_plan is None:
        wallet_plan = 'keep' if wallet else ('none' if energy else 'add_main_currency_and_skins')
    doc = {'schema': SCHEMA, 'wallet': bool(wallet), 'wallet_currency': wallet_currency if wallet else None,
           'wallet_plan': wallet_plan, 'items': bool(items), 'skins': bool(skins), 'energy': bool(energy), 'kind': kind,
           'evidence': dict(evidence or {}), 'written_by': written_by}
    if rules_revision:
        doc['rules_revision'] = rules_revision
    errs = validate(doc)
    if errs:
        raise ValueError('; '.join(errs))
    return doc


def validate(doc):
    """Problems with a capability record (empty list = valid). Same rules as economy_capabilities.schema.json."""
    if not isinstance(doc, dict):
        return ['not a JSON object']
    errs = []
    if doc.get('schema') != SCHEMA:
        errs.append('schema must be %s' % SCHEMA)
    for k in KEYS:
        if not isinstance(doc.get(k), bool):
            errs.append('%s must be true or false' % k)
    allowed = set(KEYS) | {'schema', 'wallet_currency', 'wallet_plan', 'kind', 'evidence', 'written_by', 'rules_revision'}
    errs += ['unknown field %s' % k for k in sorted(set(doc) - allowed)]
    plan = doc.get('wallet_plan')
    if plan is not None and plan not in PLANS:
        errs.append('wallet_plan must be one of %s' % ', '.join(PLANS))
    if doc.get('wallet') is True and plan not in (None, 'keep'):
        errs.append('wallet true needs wallet_plan keep')
    if doc.get('wallet') is False and doc.get('energy') is True and plan not in (None, 'none'):
        errs.append('no wallet but energy: wallet_plan none (+3 energy rows, ECON-SHORTCUT no_coin_with_energy)')
    if doc.get('wallet') is False and doc.get('energy') is False and plan not in (None, 'add_main_currency_and_skins'):
        errs.append('no wallet and no energy: wallet_plan add_main_currency_and_skins (Saul 2026-11-04)')
    return errs


def load(path):
    doc = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    errs = validate(doc)
    if errs:
        raise ValueError('%s: %s' % (path, '; '.join(errs)))
    return doc


def no_wallet_substitutes(cap, rules):
    """What replaces each B-based reward when the game has no wallet, read from the rules table params."""
    sc, rv, nc = rules['ECON-SHORTCUT'], rules['ECON-REVISIT'], rules['ECON-NOCUR']
    out = {'B': {'rule': 'ECON-B', 'value': None, 'why': 'no coin currency (energy is not a coin): there is no B to find'}}
    if cap['items']:
        out['result_x2'] = {'rule': 'ECON-NOCUR', 'doubles': 'items_picked_up_this_round', 'per_round': nc['per_round'],
                            'if_none_picked': 'no_x2_button', 'never': 'score'}
    else:
        out['result_x2'] = {'rule': 'ECON-NOCUR', 'doubles': None, 'why': 'nothing to pick up this round: no x2 button',
                            'never': 'score'}
    for key, p, rule in (('shortcut', sc, 'ECON-SHORTCUT'), ('revisit', rv, 'ECON-REVISIT')):
        if cap['energy']:
            w = p['no_coin_with_energy']
            out[key] = {'rule': rule, 'currency': w['currency'], 'amount': w['amount'], 'times': p['times']}
        else:
            out[key] = {'rule': rule, 'action': p['no_coin_no_energy'],
                        'then': 'pay %sB of the new coin once (rerun with --B after adding the coin)' % p['reward_B']}
    if not cap['energy']:
        out['wallet'] = {'action': 'add_main_currency_and_skins', 'by': 'Saul 2026-11-04',
                         'then': 'rerun make_economy_config.py with --B and --systems ...,skins (capabilities wallet true)'}
    return out


def _skip(path, root):
    parts = set(Path(path).relative_to(root).parts[:-1])
    return bool(parts & SKIP_PARTS) or any(n in Path(path).name for n in SKIP_NAMES) or '.test.' in Path(path).name \
        or Path(path).name.endswith('.d.ts')


def _strip_comment(line):
    i = line.find('//')
    return line if i < 0 else line[:i]


def scan_hardcoded(root):
    """[{file, line, text, name, number}] for reward numbers written into game scripts."""
    root = Path(root)
    base = root / 'assets' if (root / 'assets').is_dir() else root
    hits = []
    for p in sorted(base.rglob('*')):
        if not p.is_file() or p.suffix.lower() not in SCRIPT_SUFFIXES or _skip(p, root):
            continue
        try:
            text = p.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        if len(text) > 2_000_000 or '\n' not in text[:20000] and len(text) > 200_000:
            continue  # minified bundle, not hand-written game code
        for n, line in enumerate(text.splitlines(), 1):
            if ALLOW_MARK in line:
                continue
            code = _strip_comment(line)
            for rx in HARDCODED:
                m = rx.search(code)
                if m and float(m.group('num')) != 0:
                    hits.append({'file': p.relative_to(root).as_posix(), 'line': n, 'text': line.strip()[:160],
                                 'name': m.group('name'), 'number': m.group('num')})
                    break
    return hits


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('scan')
    s.add_argument('--project', type=Path, required=True)
    s.add_argument('--json', action='store_true')
    v = sub.add_parser('show')
    v.add_argument('--file', type=Path, required=True)
    a = ap.parse_args(argv)
    if a.cmd == 'show':
        try:
            print(json.dumps(load(a.file), ensure_ascii=False, indent=2))
            return 0
        except (OSError, ValueError) as exc:
            print('invalid: %s' % exc, file=sys.stderr)
            return 2
    if not a.project.is_dir():
        print('not a directory: %s' % a.project, file=sys.stderr)
        return 2
    hits = scan_hardcoded(a.project)
    if a.json:
        print(json.dumps({'hardcoded_rewards': hits}, ensure_ascii=False, indent=2))
    else:
        for h in hits:
            print('%s:%d  %s   <- reward number %s written in code; read it from economy_config.json' % (
                h['file'], h['line'], h['text'], h['number']))
        print('%d hard-coded reward number(s)' % len(hits))
    return 1 if hits else 0


if __name__ == '__main__':
    sys.exit(main())
