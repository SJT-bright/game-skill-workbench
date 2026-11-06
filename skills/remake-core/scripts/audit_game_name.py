#!/usr/bin/env python3
"""The game's own name shown as text in the game (生成时预防 R4O1, Saul 2026-11-05: no game name in the game).

Read only, under a second per project. The same check runs inside tiktok_finalize `source` and `sync`
(tiktok_finalize_steps/game_name_scan.py, which documents where the name comes from and the levels).

  python3 audit_game_name.py --project <Cocos project> [--project ...] [--board remake|localize] [--json]

Exit codes: 0 nothing blocks (warnings may be listed), 1 a new game begun after the rule shows its name, 2 bad input.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from tiktok_finalize_steps import game_name_scan as G  # noqa: E402
from tiktok_finalize_steps import policy as P  # noqa: E402
import feature_policy  # noqa: E402


def check(project, board=None):
    root = Path(project)
    pol = P.decide(project=root)['policy']
    board = board or feature_policy.board_of(root)[0]
    after, why = G.started_after_rule(root)
    level = G.level_of(pol, board, after)
    out = {'project': str(root), 'policy': pol, 'board': board, 'level': level, 'why': why}
    if level == 'skip':
        out.update(names=[], hits=[], texts=0)
        return out
    found = G.scan(root)
    out.update(names=[{'name': n, 'from': s} for n, s in found['names']], hits=found['hits'], texts=found['texts'],
               seconds=found['seconds'])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', action='append', required=True, type=Path)
    ap.add_argument('--board', choices=('remake', 'localize'))
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    rows = []
    for p in a.project:
        if not p.is_dir():
            print('not a folder: %s' % p, file=sys.stderr)
            return 2
        rows.append(check(p, a.board))
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
    else:
        for r in rows:
            print('%s  %s  policy=%s board=%s  names=%s  hits=%d  (%s)' % (
                r['level'].upper(), r['project'], r['policy'], r['board'],
                ', '.join(x['name'] for x in r['names']) or '-', len(r['hits']), r['why']))
            if r['hits'] and r['level'] != 'skip':
                print('   ' + G.message(r['hits']))
    return 1 if any(r['level'] == 'block' and r['hits'] for r in rows) else 0


if __name__ == '__main__':
    sys.exit(main())
