#!/usr/bin/env python3
"""Weekly League (simulated ranking) check — references/ranking-league.md (user 2026-10-21).

Both boards record a decision in docs/league/decision.json (schema league_decision.v1):
  remake   decision "add" when all four questions are yes (win/lose or score each round, a number that keeps
           growing, enough content: >= 30 levels or endless, comparable between players), otherwise "skip".
  localize decision "none" (英化不加排名) or "keep_original" (the original game already had one; kept as it was).
           A localize project must not contain the league module.
For "add":
  - assets/**/LeagueSim.ts is the skill's assets/league/LeagueSim.ts unchanged (SHA-256)
  - assets/**/league-config.json passes the simulation (league_harness.mjs, Node): config ranges, never #1,
    5-6% of rounds go down, every round moves up, fast then slow, rivals follow, board consistent,
    deterministic after save/load, weekly settlement (10 league skins in order, then coins only, claim once),
    clock back / long absence, unclaimed weeks, calibration of casual/regular/heavy players
  - unlock_table.json has exactly the 10 league skins (unlock "league", no ads, no coins)
  - player-visible text never claims real/national/online players, and says somewhere that rivals are
    computer players (rules popup)
Usage:
  python audit_league.py --project <game> [--board localize|remake] [--binding review.json] --out report.json
Exit codes: 0 pass, 1 fail, 2 bad input. Simulation and static text only: the league page itself is checked
in the browser (RANK-02) and by audit_page_richness.py.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
from feature_policy import read_record
import re
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
REFERENCE = HERE.parent / 'assets' / 'league' / 'LeagueSim.ts'
HARNESS = HERE / 'league_harness.mjs'
GAME_TYPES = {'level_progression', 'xp_level', 'power_growth', 'endless_score', 'time_attack',
              'few_levels', 'relaxing_no_fail', 'one_off_content', 'other'}
QUESTIONS = ('win_lose_or_score', 'ever_growing_number', 'enough_content', 'comparable')
SKIP_DIRS = {'node_modules', 'library', 'temp', 'build', 'local', 'profiles', '.git', 'settings', 'packages'}
BANNED = re.compile(r'\b(nation(al|wide)?|countrywide|world\s*-?\s*wide|global\s+(rank|ranks|ranking|rankings|players|leaderboard)|'
                    r'real\s+(players|people|opponents|rivals)|players?\s+online|online\s+(now|players)|live\s+players)\b'
                    r'|全国|真实玩家|在线人数|真人', re.I)
DISCLOSE = re.compile(r'\b(computer|ai|simulated|virtual|cpu|bot)\s*-?\s*(players?|rivals?|opponents?|racers?|competitors?)\b', re.I)
LITERAL = re.compile(r'"((?:[^"\\\n]|\\.){3,300})"|\'((?:[^\'\\\n]|\\.){3,300})\'|`([^`]{3,300})`')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def files(root, names=None, suffixes=None):
    out = []
    for dirpath, dirs, fs in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in fs:
            if (names and f in names) or (suffixes and Path(f).suffix.lower() in suffixes):
                out.append(Path(dirpath) / f)
    return sorted(out)


def find_table(proj):
    for c in (proj / 'assets/resources/config/unlock_table.json', proj / 'docs/economy/unlock_table.json'):
        if c.is_file():
            return c
    return None


def player_text(proj):
    """String literals from game code plus copy files: what a player could read."""
    texts = []
    for p in files(proj / 'assets', suffixes={'.ts', '.js'}):
        if p.name == 'LeagueSim.ts':
            continue
        try:
            src = p.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        for m in LITERAL.finditer(src):
            s = next(g for g in m.groups() if g is not None)
            if re.search(r'[A-Za-z一-鿿]{2,}\s', s) or re.search(r'[一-鿿]', s):
                texts.append((p.relative_to(proj).as_posix(), s))
    extra = files(proj / 'assets', suffixes={'.json'}) + [p for p in (proj / 'COPY_EN.md', proj / 'docs/copy/copy-table.csv') if p.is_file()]
    extra += files(proj / 'docs/copy', suffixes={'.md', '.csv', '.json'}) if (proj / 'docs/copy').is_dir() else []
    for p in dict.fromkeys(extra):
        if p.name in ('league-config.json', 'unlock_table.json') or p.suffix == '.json' and p.stat().st_size > 2_000_000:
            continue
        try:
            for line in p.read_text(encoding='utf-8', errors='replace').splitlines():
                if line.strip():
                    texts.append((p.relative_to(proj).as_posix(), line.strip()[:300]))
        except OSError:
            continue
    return texts


def run_harness(module, config):
    node = shutil.which('node')
    if not node:
        return None, 'Node.js not found: install Node.js (any version >= 18) to run the league simulation'
    with tempfile.TemporaryDirectory(prefix='league-') as tmp:
        mod = Path(tmp) / 'LeagueSim.mjs'
        mod.write_bytes(Path(module).read_bytes())
        env = dict(os.environ, TZ='UTC')
        try:
            r = subprocess.run([node, str(HARNESS), str(mod), str(config)], capture_output=True, text=True, timeout=300, env=env)
        except subprocess.TimeoutExpired:
            return None, 'league simulation timed out'
        try:
            return json.loads(r.stdout.strip().splitlines()[-1])['checks'], None
        except (ValueError, IndexError, KeyError):
            return None, 'league simulation crashed: ' + (r.stderr or r.stdout)[-400:]


def audit(proj, board, reference):
    checks = []

    def add(cid, ok, detail):
        checks.append({'id': cid, 'passed': bool(ok), 'detail': detail})

    core = read_record(proj, 'docs/modules.json')
    explicit = read_record(proj, 'docs/league/decision.json')
    if not explicit and core.get('schema') == 'game_modules.v1' and str(core.get('asked', '')).strip():
        lingering = files(proj / 'assets', names={'LeagueSim.ts', 'league-config.json'})
        add('default_disabled', not lingering, 'game_modules.v1 records default league disabled; ' +
            ('no legacy module files' if not lingering else 'remove unrequested league files'))
        return checks, 'none' if board == 'localize' else 'skip'
    dec_path = proj / 'docs/league/decision.json'
    try:
        dec = json.loads(dec_path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as exc:
        add('decision_recorded', False, 'docs/league/decision.json missing or not JSON (%s): record whether this game gets a '
            'Weekly League (references/ranking-league.md)' % exc)
        return checks, None
    decision = dec.get('decision')
    modules = files(proj / 'assets', names={'LeagueSim.ts'})
    configs = files(proj / 'assets', names={'league-config.json'})
    if dec.get('schema') != 'league_decision.v1':
        add('decision_recorded', False, 'decision.json schema must be league_decision.v1')
        return checks, decision
    if decision in ('skip', 'none'):
        add('default_disabled', not modules and not configs, 'explicit disabled league decision; no league files' if not modules and not configs else 'disabled decision but league files remain')
        return checks, decision
    if board == 'localize' and decision != 'add':
        ok = decision in ('none', 'keep_original') and not modules and not configs
        add('localize_no_new_league', ok,
            '英化不加排名：decision %r, league files in assets: %s' % (decision, [p.relative_to(proj).as_posix() for p in modules + configs] or 'none')
            if not ok else ('英化：没有新增排名' + ('（原游戏自带的排名保留原样）' if decision == 'keep_original' else '')))
        if decision == 'keep_original':
            add('original_kept_note', bool(str(dec.get('notes', '')).strip()), 'keep_original needs notes: where the original ranking is and that its logic is unchanged')
        return checks, decision
    answers = dec.get('answers') if isinstance(dec.get('answers'), dict) else {}
    typed = dec.get('game_type') in GAME_TYPES and all(isinstance(answers.get(q), bool) for q in QUESTIONS)
    reasons = all(str((dec.get('evidence') or {}).get(q, '')).strip() for q in QUESTIONS) if isinstance(dec.get('evidence'), dict) else False
    all_yes = typed and all(answers[q] for q in QUESTIONS)
    if not typed or not reasons or decision not in ('add', 'skip'):
        add('decision_recorded', False, 'decision.json needs decision add|skip, game_type (%s), answers and evidence for %s'
            % ('/'.join(sorted(GAME_TYPES)), ', '.join(QUESTIONS)))
        return checks, decision
    add('decision_matches_answers', decision != 'add' or all_yes,
        ('four yes -> add' if all_yes else 'not all yes -> skip') + ('' if (decision == 'add') == all_yes else
                                                                    ' (decision says %s: fix the decision or the answers)' % decision))
    if decision == 'skip':
        add('skip_has_no_league', not modules and not configs, 'skip: no league files in assets' if not modules and not configs
            else 'skip but league files are in assets: ' + ', '.join(p.relative_to(proj).as_posix() for p in modules + configs))
        return checks, decision
    if len(modules) != 1 or len(configs) != 1:
        add('league_files', False, 'add needs exactly one assets/**/LeagueSim.ts and one assets/**/league-config.json (found %d and %d)'
            % (len(modules), len(configs)))
        return checks, decision
    same = sha(modules[0]) == sha(reference)
    add('module_unchanged', same, 'LeagueSim.ts is the skill copy' if same else
        'LeagueSim.ts differs from the skill copy (assets/league/LeagueSim.ts): copy it again unchanged; tune league-config.json only')
    try:
        cfg = json.loads(configs[0].read_text(encoding='utf-8-sig'))
    except ValueError as exc:
        add('config_json', False, 'league-config.json is not JSON: %s' % exc)
        return checks, decision
    sim, err = run_harness(modules[0], configs[0])
    if err:
        add('simulation', False, err)
    else:
        for c in sim:
            add('sim_' + c['id'], c['passed'], c['detail'])
    for word, field in (('title', cfg.get('title', '')), ('metric_label', cfg.get('metric_label', ''))):
        if BANNED.search(str(field)):
            add('config_' + word, False, 'league-config.json %s %r claims real/national players' % (word, field))
    table = find_table(proj)
    skins = set(cfg.get('league_skins') or [])
    if not table:
        add('league_skins_in_table', False, 'unlock_table.json not found: the 10 league skins must be items with "unlock": "league"')
    else:
        try:
            data = json.loads(table.read_text(encoding='utf-8-sig'))
            rows = data.get('items') if isinstance(data, dict) else data
            league = [r for r in rows if isinstance(r, dict) and str(r.get('unlock', '')).lower() == 'league']
            ids = {str(r.get('id')) for r in league}
            bad = [r.get('id') for r in league if r.get('ads') or r.get('coins')]
            ok = len(league) == 10 and ids == skins and not bad
            add('league_skins_in_table', ok, '10 league skins listed, league-only, no ads or coins' if ok else
                'unlock_table has %d league items %s; league-config lists %s%s' % (len(league), sorted(ids), sorted(skins),
                                                                                  ('; ads/coins on ' + ', '.join(map(str, bad))) if bad else ''))
        except (OSError, ValueError, AttributeError, TypeError) as exc:
            add('league_skins_in_table', False, 'unlock_table.json unreadable: %s' % exc)
    texts = player_text(proj)
    claims = [(f, s) for f, s in texts if BANNED.search(s)]
    add('no_real_player_claims', not claims, 'no "national / worldwide / real players / online" wording' if not claims else
        'remove these claims (the rivals are simulated): ' + '; '.join('%s: %s' % (f, s[:80]) for f, s in claims[:5]))
    disclosed = [(f, s) for f, s in texts if DISCLOSE.search(s)]
    add('rules_say_computer_rivals', bool(disclosed), ('rules text found: ' + disclosed[0][1][:80]) if disclosed else
        'the league rules popup must say the rivals are computer players, e.g. "League rivals are computer players."')
    return checks, decision


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--board', choices=['localize', 'remake'])
    ap.add_argument('--binding', type=Path, help='known-issue review JSON whose "binding" is copied into the report')
    ap.add_argument('--reference', type=Path, default=REFERENCE, help=argparse.SUPPRESS)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    proj = a.project.resolve()
    if not (proj / 'assets').is_dir():
        ap.error('%s is not a Cocos project (no assets folder)' % proj)
    board_file = proj / 'docs/board.txt'
    recorded = board_file.read_text(encoding='utf-8').strip().lower() if board_file.is_file() else ''
    if a.board and recorded in ('localize', 'remake') and a.board != recorded:
        ap.error('--board %s differs from docs/board.txt (%s)' % (a.board, recorded))
    board = a.board or recorded
    if board not in ('localize', 'remake'):
        ap.error('board unknown: pass --board or write docs/board.txt')
    checks, decision = audit(proj, board, a.reference)
    failed = [c for c in checks if not c['passed']]
    report = {'tool': 'audit_league', 'schema': 1, 'board': board, 'decision': decision, 'checks': checks,
              'checked': len(checks), 'failed': len(failed), 'passed': not failed and bool(checks),
              'status': 'pass' if not failed and checks else 'fail',
              'reference_sha256': sha(a.reference) if a.reference.is_file() else None,
              'boundary': 'Decision record, unchanged module, simulation of the config and static text. The league page, '
                          'result-page rank change and weekly popup are checked in the browser (RANK-02).'}
    if a.binding:
        try:
            b = json.loads(a.binding.read_text(encoding='utf-8')).get('binding')
        except (OSError, ValueError) as exc:
            ap.error('binding: %s' % exc)
        if not isinstance(b, dict):
            ap.error('no binding object in %s' % a.binding)
        report['binding'] = b
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'decision': decision, 'checked': len(checks), 'failed': len(failed),
                      'found': [{'id': c['id'], 'detail': c['detail'][:200]} for c in failed][:8], 'report': str(a.out)},
                     ensure_ascii=False))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
