#!/usr/bin/env python3
"""What a game HAS, written once while the game is made and read by every diagnosis and check (P20 第 3 点「能力先判」,
问题普查 20261104: diagnose_misread 26, rule_conflict 17, checker_unsupported 11, checker_false_block 64 games).

Before this each check guessed on its own: a game without coins was told to find B (旋律动物园, 合成大西瓜, 人鱼逃脱 ...);
a no-coin, no-item game was asked for a result x2 by one rule and told to show none by another (弹弹球); a level without a
pause key or with no ad entries listed had the case skipped (美人鱼, 割草).

Two files, one view:
  docs/economy/economy_capabilities.json  wallet / items / skins / energy. Written by make_economy_config.py (K1 批,
                                          economy_capabilities.py). Not copied here.
  docs/game_capabilities.json             pause_button, ad_entries, no_ad_roles. Written by this script's `write`
                                          (schema remake-core/references/game_capabilities.schema.json).

load(project) merges them. verdict(caps, need) answers 'yes' | 'no' | 'unknown' with the reason and the file; checks use
feature_policy.applies(rule, board, project) (capability rules: CAP_RULES there): no -> not_applicable with the
record's reason, no record -> not_run naming the missing field. Never a guess.

CLI
  python3 game_capabilities.py write --project <game> (--pause-button <node path> | --no-pause-button "why")
          (--ad-entry role=<node path> ... | --no-ad-entries "why") [--no-ad-role double="why"] [--evidence k=v]
  python3 game_capabilities.py show --project <game>          exit 0, 2 when a record is invalid
  python3 game_capabilities.py adapter --project <game> --adapter in.json --out out.json [--policy new|legacy]
          fills the runtime adapter from the record (resume_play.pause_button, ad_outcome.none), exit 2 = not_run
"""
import argparse
import json
import re
import sys
from pathlib import Path

SCHEMA = 'game_capabilities.v1'
RECORD = Path('docs') / 'game_capabilities.json'
ECONOMY_RECORD = Path('docs') / 'economy' / 'economy_capabilities.json'
ECONOMY_KEYS = ('wallet', 'items', 'skins', 'energy')
ROLE = re.compile(r'^[a-z][a-z0-9_]{1,30}$')     # same as runtime_regression adEntriesProblems
FIELDS = {'schema', 'pause_button', 'ad_entries', 'no_ad_roles', 'evidence', 'written_by'}

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _none(v):
    return isinstance(v, dict) and set(v) == {'none'} and isinstance(v['none'], str) and bool(v['none'].strip())


def validate(doc):
    """Problems with docs/game_capabilities.json ([] = valid)."""
    if not isinstance(doc, dict):
        return ['not a JSON object']
    errs = [] if doc.get('schema') == SCHEMA else ['schema must be %s' % SCHEMA]
    errs += ['unknown field %s' % k for k in sorted(set(doc) - FIELDS)]
    pb = doc.get('pause_button')
    if 'pause_button' in doc and not ((isinstance(pb, str) and pb.strip()) or _none(pb)):
        errs.append('pause_button must be a node path or {"none": "why the level has no pause / settings key"}')
    ae = doc.get('ad_entries')
    if 'ad_entries' in doc:
        if _none(ae):
            pass
        elif not isinstance(ae, list) or not ae:
            errs.append('ad_entries must be a nonempty list of {role, button} or {"none": "why no rewarded ad"}')
        else:
            for i, e in enumerate(ae):
                if not isinstance(e, dict) or not ROLE.match(str(e.get('role', ''))):
                    errs.append('ad_entries[%d].role must be a lower-case word (double, revive, home_gift ...)' % i)
                elif not (isinstance(e.get('button'), str) and e['button'].strip()):
                    errs.append('ad_entries[%d].button must be the node path of the button' % i)
                elif 'states' in e and not (isinstance(e['states'], list) and e['states']):
                    errs.append('ad_entries[%d].states must be a nonempty list (runtime adapter ad_entries form)' % i)
    nr = doc.get('no_ad_roles')
    if 'no_ad_roles' in doc and not (isinstance(nr, dict) and all(
            ROLE.match(k) and isinstance(v, str) and v.strip() for k, v in nr.items())):
        errs.append('no_ad_roles must map a role (double, revive) to why the game has no such button')
    return errs


def _read(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig')), None
    except FileNotFoundError:
        return None, None
    except (OSError, ValueError) as exc:
        return None, '%s unreadable: %s' % (path, exc)


def load(project=None, record=None, economy=None):
    """{field: value or None, 'source': {field: file}, 'problems': [...]} from the two records.
    project: game folder; record / economy: explicit files (tests, a runner given --capabilities)."""
    caps = {k: None for k in ECONOMY_KEYS + ('pause_button', 'ad_entries', 'no_ad_roles')}
    caps.update({'source': {}, 'problems': [], 'project': str(project) if project else None})
    root = Path(project) if project else None
    eco_path = Path(economy) if economy else (root / ECONOMY_RECORD if root else None)
    rec_path = Path(record) if record else (root / RECORD if root else None)
    if eco_path:
        doc, err = _read(eco_path)
        if err:
            caps['problems'].append(err)
        elif doc is not None:
            try:
                from economy_capabilities import validate as eco_validate
                bad = eco_validate(doc)
            except ImportError:   # remake-core without the K1 file: shape only
                bad = [] if all(isinstance(doc.get(k), bool) for k in ECONOMY_KEYS) else ['wallet/items/skins/energy must be true/false']
            if bad:
                caps['problems'].append('%s: %s' % (eco_path, '; '.join(bad)))
            else:
                for k in ECONOMY_KEYS:
                    caps[k] = doc[k]
                    caps['source'][k] = str(eco_path)
    if rec_path:
        doc, err = _read(rec_path)
        if err:
            caps['problems'].append(err)
        elif doc is not None:
            bad = validate(doc)
            if bad:
                caps['problems'].append('%s: %s' % (rec_path, '; '.join(bad)))
            else:
                for k in ('pause_button', 'ad_entries', 'no_ad_roles'):
                    if k in doc:
                        caps[k] = doc[k]
                        caps['source'][k] = str(rec_path)
    return caps


def _missing(field):
    if field in ECONOMY_KEYS:
        return ('not recorded: %s has no "%s" (make_economy_config.py writes it; a game without coins: --no-wallet)'
                % (ECONOMY_RECORD.as_posix(), field))
    return ('not recorded: %s has no "%s" (game_capabilities.py write --project <game> %s)'
            % (RECORD.as_posix(), field, {'pause_button': '--pause-button <path> | --no-pause-button "why"',
                                          'ad_entries': '--ad-entry role=<path> | --no-ad-entries "why"'}.get(field, '')))


def ad_roles(caps):
    """Set of ad roles the record lists, or None when ad_entries is not recorded."""
    ae = caps.get('ad_entries')
    if ae is None:
        return None
    return set() if _none(ae) else {e['role'] for e in ae}


def verdict(caps, need):
    """('yes' | 'no' | 'unknown', reason). need: wallet, items, skins, energy, pause_button, ad_entries,
    no_wallet (wallet false), ad_role:<role>."""
    src = caps.get('source', {})
    if need == 'no_wallet':
        v, why = verdict(caps, 'wallet')
        return ({'yes': 'no', 'no': 'yes'}.get(v, v), why)
    if need in ECONOMY_KEYS:
        v = caps.get(need)
        if v is None:
            return 'unknown', _missing(need)
        return ('yes' if v else 'no'), '%s=%s (%s)' % (need, 'true' if v else 'false', src.get(need))
    if need == 'pause_button':
        v = caps.get('pause_button')
        if v is None:
            return 'unknown', _missing('pause_button')
        if _none(v):
            return 'no', 'pause_button none: %s (%s)' % (v['none'], src.get('pause_button'))
        return 'yes', 'pause_button %s (%s)' % (v, src.get('pause_button'))
    if need == 'ad_entries':
        roles = ad_roles(caps)
        if roles is None:
            return 'unknown', _missing('ad_entries')
        if not roles:
            return 'no', 'ad_entries none: %s (%s)' % (caps['ad_entries']['none'], src.get('ad_entries'))
        return 'yes', 'ad_entries %s (%s)' % (', '.join(sorted(roles)), src.get('ad_entries'))
    if need.startswith('ad_role:'):
        role = need[8:]
        none = caps.get('no_ad_roles') or {}
        if role in none:
            return 'no', 'no_ad_roles.%s: %s (%s)' % (role, none[role], src.get('no_ad_roles'))
        if role == 'double' and caps.get('wallet') is False and caps.get('items') is False:
            # rules table ECON-NOCUR: no coin and nothing picked up this round -> no x2 button (弹弹球 rule_conflict)
            return 'no', 'no coin and no items: ECON-NOCUR shows no result x2 (%s)' % src.get('wallet')
        roles = ad_roles(caps)
        if roles is None:
            return 'unknown', _missing('ad_entries')
        if role in roles:
            return 'yes', 'ad_entries has role %s (%s)' % (role, src.get('ad_entries'))
        return 'no_entry', 'ad_entries lists no role %s and no_ad_roles does not say why (%s)' % (role, src.get('ad_entries'))
    raise KeyError(need)


def make(pause_button=None, ad_entries=None, no_ad_roles=None, evidence=None, written_by='game_capabilities.py write'):
    doc = {'schema': SCHEMA}
    if pause_button is not None:
        doc['pause_button'] = pause_button
    if ad_entries is not None:
        doc['ad_entries'] = ad_entries
    if no_ad_roles:
        doc['no_ad_roles'] = dict(no_ad_roles)
    doc['evidence'] = dict(evidence or {})
    doc['written_by'] = written_by
    errs = validate(doc)
    if errs:
        raise ValueError('; '.join(errs))
    return doc


def fill_adapter(adapter, caps, policy='new'):
    """Runtime adapter + record -> (adapter, notes, not_run). Fills only what the adapter leaves out:
    resume_play.pause_button from pause_button; ad_outcome.none.<role> from no_ad_roles / ECON-NOCUR; ad_entries from
    record entries that carry states. not_run lists what a new game's record still lacks (the check would guess)."""
    out = json.loads(json.dumps(adapter))
    notes, missing = [], []
    rp = out.get('resume_play')
    if isinstance(rp, dict) and 'n/a' not in rp and 'pause_button' not in rp:
        v, why = verdict(caps, 'pause_button')
        if v == 'unknown':
            missing.append(why)
        else:
            rp['pause_button'] = caps['pause_button']
            notes.append('resume_play.pause_button from the record: ' + why)
    outcome = out.get('ad_outcome')
    if not (isinstance(outcome, dict) and 'n/a' in outcome):
        for role in ('double', 'revive'):
            v, why = verdict(caps, 'ad_role:' + role)
            have = {e.get('role') for e in out.get('ad_entries') or [] if isinstance(e, dict)}
            if role in have:
                continue
            if v == 'no':
                if not isinstance(out.get('ad_outcome'), dict):
                    out['ad_outcome'] = {}
                out['ad_outcome'].setdefault('none', {}).setdefault(role, 'capability record: ' + why)
                notes.append('ad_outcome.none.%s from the record: %s' % (role, why))
            elif v == 'unknown':
                missing.append(why)
        if not out.get('ad_entries'):
            staged = [dict({'id': e.get('id') or e['role']}, **{k: e[k] for k in ('role', 'button', 'states')})
                      for e in (caps.get('ad_entries') or []) if isinstance(e, dict) and e.get('states')]
            if staged:
                out['ad_entries'] = staged
                notes.append('ad_entries from the record: ' + ', '.join(e['id'] for e in staged))
            elif ad_roles(caps):
                missing.append('ad_entries: the record lists %s but no entry has "states" (the real steps that show '
                               'the button); the ad_entries suite would not run' % ', '.join(sorted(ad_roles(caps))))
    return out, notes, (missing if policy != 'legacy' else [])


def _kv(items, what):
    out = {}
    for s in items or []:
        if '=' not in s:
            raise SystemExit('%s must be key=value: %s' % (what, s))
        k, v = s.split('=', 1)
        out[k.strip()] = v.strip()
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    w = sub.add_parser('write', help='write docs/game_capabilities.json')
    w.add_argument('--project', type=Path, required=True)
    g = w.add_mutually_exclusive_group(required=True)
    g.add_argument('--pause-button', help='node path of the in-level pause / settings key')
    g.add_argument('--no-pause-button', metavar='WHY')
    h = w.add_mutually_exclusive_group(required=True)
    h.add_argument('--ad-entry', action='append', metavar='ROLE=PATH', help='double=Canvas/Result/btn_x2 (repeat)')
    h.add_argument('--no-ad-entries', metavar='WHY')
    w.add_argument('--no-ad-role', action='append', metavar='ROLE=WHY')
    w.add_argument('--evidence', action='append', metavar='KEY=FILE:LINE')
    s = sub.add_parser('show')
    s.add_argument('--project', type=Path, required=True)
    a = sub.add_parser('adapter', help='fill a runtime adapter from the record')
    a.add_argument('--project', type=Path, required=True)
    a.add_argument('--adapter', type=Path, required=True)
    a.add_argument('--out', type=Path, required=True)
    a.add_argument('--policy', choices=['new', 'legacy'], default='new')
    args = ap.parse_args(argv)
    if not args.project.is_dir():
        print('not_run: not a directory: %s' % args.project, file=sys.stderr)
        return 2
    if args.cmd == 'write':
        try:
            entries = ({'none': args.no_ad_entries} if args.no_ad_entries else
                       [{'role': k, 'button': v} for k, v in _kv(args.ad_entry, '--ad-entry').items()])
            doc = make({'none': args.no_pause_button} if args.no_pause_button else args.pause_button, entries,
                       _kv(args.no_ad_role, '--no-ad-role'), _kv(args.evidence, '--evidence'))
        except ValueError as exc:
            print('refused: %s' % exc, file=sys.stderr)
            return 1
        path = args.project / RECORD
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'out': str(path)}, ensure_ascii=False))
        return 0
    caps = load(args.project)
    if args.cmd == 'show':
        view = {k: v for k, v in caps.items() if k != 'project'}
        view['verdicts'] = {n: verdict(caps, n) for n in ECONOMY_KEYS + ('pause_button', 'ad_entries', 'ad_role:double', 'ad_role:revive')}
        print(json.dumps(view, ensure_ascii=False, indent=2))
        return 2 if caps['problems'] else 0
    try:
        adapter = json.loads(args.adapter.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        print('not_run: adapter unreadable: %s' % exc, file=sys.stderr)
        return 2
    filled, notes, missing = fill_adapter(adapter, caps, args.policy)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(filled, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'out': str(args.out), 'from_record': notes, 'not_run': missing, 'problems': caps['problems']},
                     ensure_ascii=False, indent=2))
    return 2 if (missing or caps['problems']) else 0


if __name__ == '__main__':
    sys.exit(main())
