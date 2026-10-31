#!/usr/bin/env python3
"""英化范围回归（v7.8）：英化不补关、不加皮肤和经济（Saul 2026-10-28，取代 2026-10-21～10-24 的“英化＋优化”）。

Until v7.8 the shared library still carried the old English rules: audit_level_plan.py demanded that an English game
with fewer than 70 levels be padded to exactly 70, known-issues.json made ECON-01/02 (skins, ad trial, map unlock)
mandatory for every English game, and about forty doc lines told models to pad levels, add skins, a tutorial, a top
bar and a level map. This test pins the current rules and fails if the old wording comes back.
Run: PYTHONDONTWRITEBYTECODE=1 python3 -B test_localize_scope.py
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
CATALOG = HERE.parent / 'assets' / 'known-issues.json'
PACK = HERE.parents[1]
PACK_SKILLS = ('cocos-game-check', 'cocos-game-to-english', 'remake-core', 'remake-art', 'remake-game', 'remake-levels',
               'remake-economy', 'remake-skins', 'remake-ads', 'remake-onboarding', 'remake-copy', 'game-audio-library',
               'chrome-mobile-testing', 'mobile-touch-computer-use')
# Exact phrases of the void rules (each one was in v7.7.5). History notes like 取代 10-24 的“不到 70 补到 70” are fine.
STALE = ('英化至少 70', '英化至少70', '英化 ≥70', '英化≥70', '英化仍是至少 70', '英化默认至少 70', '英化原关 N≥70',
         '原有N≥70', '英化N>=70', '英化原关>=70', '补到恰好70', '补到恰好 70', '补到至少70', '不足补至70', '补到 70 关（标',
         '英化＋优化标准', '英化＋优化时', '英化＋优化：', '英化＋优化要给', '英化＋优化与重塑', '按 7 个阶段做英化＋优化',
         '英化不补**：原游戏没有复活就不加', 'keeps the 70 rule', 'keeps its own 70 rule', '英化 70 关及以上',
         'adds this to every game', 'source code to English plus optimisation', '英化 1.5 优化做完')
TEXT = ('.md', '.py', '.json', '.txt', '.js', '.cjs', '.mjs')


def rows(n):
    return [dict(level=i, layout=[i, i + 1, i + 2]) for i in range(1, n + 1)]


def run_original(original, current, explicit=None):
    from audit_level_plan import audit_original_levels
    checks = []
    audit_original_levels(original, current, lambda cid, ok, detail: checks.append((cid, ok, detail)), explicit)
    return checks


ASK = {'count': 70, 'authorized_by': 'Saul 2026-10-30', 'reason': 'Saul asked for thirty more real levels in this game'}


class LocalizeLevelCount(unittest.TestCase):
    def test_original_count_is_enough(self):
        for n in (12, 40, 69, 70, 121):
            self.assertTrue(all(ok for _, ok, _ in run_original(rows(n), rows(n))), n)

    def test_padding_to_70_is_refused(self):
        checks = run_original(rows(40), rows(40) + [dict(level=i, layout=[i, -i]) for i in range(41, 71)])
        self.assertFalse(dict((c, ok) for c, ok, _ in checks)['levels_at_least_70'])
        self.assertIn('不补关', [d for c, _, d in checks if c == 'levels_at_least_70'][0])

    def test_levels_the_user_asked_for_need_explicit_total(self):
        current = rows(40) + [dict(level=i, layout=[i, -i]) for i in range(41, 71)]
        self.assertTrue(all(ok for _, ok, _ in run_original(rows(40), current, ASK)))
        repeat = rows(40) + [dict(level=i, layout=[1, 2, 3]) for i in range(41, 71)]
        self.assertFalse(all(ok for _, ok, _ in run_original(rows(40), repeat, ASK)))

    def test_plan_rows_marked_new_are_refused_unless_asked(self):
        from make_level_plan import make
        from audit_level_plan import audit_plan

        def count(plan):
            checks = {}
            audit_plan(plan, None, lambda cid, ok, detail: checks.update({cid: ok}), 'localize')
            return checks['levels_at_least_70']
        plan = make(40, 50, None, 19, 'Coins')
        plan['why'] = 'English game keeps its original forty levels.'
        for r in plan['levels']:
            r.pop('new', None)
        self.assertTrue(count(plan))
        for r in plan['levels'][30:]:
            r['new'] = True
        self.assertFalse(count(plan))
        plan['explicit_total'] = dict(ASK, count=40)
        self.assertTrue(count(plan))

    def test_cli_localize_keeps_the_original_count(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'assets/resources/config').mkdir(parents=True)
            (root / 'assets/resources/config/level_plan.json').write_text(json.dumps({'mode': 'levels', 'total_levels': 40}))
            original, current, report = root / 'original.json', root / 'assets/levels.json', root / 'report.json'
            original.write_text(json.dumps(rows(40)))
            cmd = [sys.executable, '-B', str(HERE / 'audit_level_plan.py'), '--project', str(root), '--board', 'localize',
                   '--original-levels', str(original), '--current-levels', str(current), '--out', str(report)]
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
            current.write_text(json.dumps(rows(40)))
            first = subprocess.run(cmd, capture_output=True, text=True, env=env)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            current.write_text(json.dumps(rows(40) + [dict(level=i, layout=[i, -i]) for i in range(41, 71)]))
            self.assertNotEqual(subprocess.run(cmd, capture_output=True, text=True, env=env).returncode, 0)


class LocalizeCatalog(unittest.TestCase):
    def setUp(self):
        self.catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
        self.items = {x['id']: x for x in self.catalog['items']}

    def test_only_the_sound_settings_are_forced_on_english_games(self):
        forced = sorted(x['id'] for x in self.catalog['items'] if 'localize' in x.get('required_boards', []))
        self.assertEqual(forced, ['AUDIO-01'])

    def test_english_notes_do_not_ask_for_levels_or_skins(self):
        for cid in ('LEVEL-01', 'LEVEL-02', 'ECON-01', 'ECON-02'):
            text = json.dumps({k: self.items[cid].get(k) for k in ('board_notes', 'steps', 'title')}, ensure_ascii=False)
            for phrase in ('补到至少70', '补到恰好', 'N<70', 'N>=70', '默认要', '不足补70'):
                self.assertNotIn(phrase, text, cid)
        self.assertIn('不补关', self.items['LEVEL-01']['board_notes']['localize'])
        self.assertIn('不加皮肤', self.items['ECON-01']['board_notes']['localize'])

    def test_board_description_has_no_skin_system(self):
        self.assertNotIn('skin/collection system', self.catalog['boards'])
        self.assertIn('no new levels', self.catalog['boards'])


class LocalizePreflight(unittest.TestCase):
    """v7.7.5 preflight with --recheck-earlier told an English game 「英化＋优化要给每个游戏加皮肤/收集系统」 (需处理)."""
    ROWS = ('关卡地图', '皮肤收集梯度', '内置板块', '排名扩展', '签到扩展', '顶部资源栏')

    def rows(self, board, files=None):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'game'
            (root / 'assets').mkdir(parents=True)
            (root / 'docs').mkdir()
            (root / 'docs/board.txt').write_text(board)
            for rel, text in (files or {}).items():
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text(text)
            out = Path(td) / 'out'
            subprocess.run([sys.executable, '-B', str(HERE / 'preflight.py'), '--project', str(root), '--board', board,
                            '--recheck-earlier', '--out', str(out)], capture_output=True, text=True,
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'), stdin=subprocess.DEVNULL)
            data = json.loads((out / 'preflight.json').read_text(encoding='utf-8'))
            return {r['check']: r['status'] for r in data['results']}

    def test_english_game_is_not_asked_for_design_stage_systems(self):
        rows = self.rows('localize')
        self.assertEqual({t: rows.get(t) for t in self.ROWS}, {t: '不适用' for t in self.ROWS})

    def test_remake_game_still_runs_them(self):
        rows = self.rows('remake')
        self.assertEqual(rows.get('内置板块'), '需处理')
        self.assertEqual(rows.get('关卡地图'), '需处理')

    def test_english_game_with_new_gameplay_is_checked(self):
        # Saul 2026-10-30: new gameplay in an English game is built with the boards; their records switch the rows on.
        rows = self.rows('localize', {'docs/modules.json': '{}'})
        self.assertNotEqual(rows.get('内置板块'), '不适用')
        self.assertNotEqual(rows.get('关卡地图'), '不适用')


class StaleWording(unittest.TestCase):
    def test_pack_docs_and_scripts_do_not_carry_the_void_rules(self):
        hits = []
        roots = [PACK / s for s in PACK_SKILLS if (PACK / s).is_dir()]
        self.assertTrue(roots, 'no pack skills found under %s' % PACK)
        files = [p for r in roots for p in r.rglob('*') if p.is_file() and p.suffix in TEXT]
        extra = PACK / '各Skill设计说明与可调整项.md'
        if extra.is_file():
            files.append(extra)
        for p in files:
            if p.name.startswith('test_') or p.name in ('PROVENANCE.json', 'distribution-manifest.json') \
                    or '__pycache__' in p.parts:
                continue
            text = p.read_text(encoding='utf-8', errors='replace')
            hits += ['%s: %s' % (p.relative_to(PACK), s) for s in STALE if s in text]
        self.assertEqual(hits, [], '\n'.join(hits[:40]))


if __name__ == '__main__':
    unittest.main(verbosity=2)
