"""The retrospective report reads existing records only, and refuses a reflection that did not read the Skill."""
import datetime
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import retrospective_report as R


class RetrospectiveReport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='复盘 report '); self.addCleanup(self.tmp.cleanup)
        home = Path(self.tmp.name).resolve()
        self.skill, self.game = home / 'skills', home / 'game 游戏'
        rule = self.skill / 'cocos-game-to-english/references/first-trial-repair.md'
        rule.parent.mkdir(parents=True); rule.write_text('# 首轮试玩修复\n\n按根因合批。\n', encoding='utf-8')
        (self.skill / 'cocos-game-to-english/PROVENANCE.json').write_text('{"revision":"fixture.1"}')
        (self.game / 'docs/timing').mkdir(parents=True)
        stages, t = [], 0
        for n, (wall, gap) in enumerate(((600, 0), (3000, 0), (9000, 2400), (1200, 0), (1200, 0)), 1):
            stages.append({'entry': n - 1, 'stage': n, 'started_at_epoch': t, 'ended_at_epoch': t + wall, 'wall_seconds': wall,
                           'completed_work_interval_union_seconds': wall - gap, 'unrecorded_seconds': gap}); t += wall
        steps = [{'name': 'build web', 'start': 3700 + i * 900, 'end': 4000 + i * 900, 'seconds': 300, 'auto': False} for i in range(3)]
        steps += [{'name': 'capture all', 'start': 7000, 'end': 11000, 'seconds': 4000, 'auto': False},
                  {'name': 'auto heartbeat', 'start': 100, 'end': 9000, 'seconds': 8900, 'auto': True}]
        (self.game / 'docs/timing/timing-summary.json').write_text(json.dumps({'stages': stages, 'steps': steps}))
        self.home = self.game / R.OUT
        self.codex = home / 'codex home'; (self.codex / 'sessions/2026/11/14').mkdir(parents=True)

    def facts(self):
        doc = R.facts(self.game, self.codex); path = R.write_json(self.home / 'facts.json', doc)
        return doc, hashlib.sha256(path.read_bytes()).hexdigest()

    def lesson(self, signals, **patch):
        rel = 'cocos-game-to-english/references/first-trial-repair.md'
        before = hashlib.sha256((self.skill / rel).read_bytes()).hexdigest()
        staged = self.home / 'patch/改动文件' / rel
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_text('# 首轮试玩修复\n\n按根因合批。\n\n## 循环上限\n\n第三次整包构建前先归因。\n', encoding='utf-8')
        body = {'decision': 'change_skill', 'reason': '每款游戏都会遇到', 'adds_check': False,
                'changes': [{'path': rel, 'before_sha256': before, 'summary': '新增循环上限'}]}
        body.update(patch)
        return {'id': 'L1', 'title': '第三阶段没有循环上限', 'kind': 'process', 'signal_ids': signals,
                'what_happened': '同一目标构建了三次', 'evidence': [{'source': 'timing-summary', 'detail': 'build web 三次'}],
                'root_cause': '合批只有原则没有界线',
                'skill_analysis': {'read_files': [rel], 'existing_rule': '按根因合批', 'why_not_prevented': '没有次数界线', 'conflicts': '无冲突'},
                'prevention': {'stage': 2, 'action': '第二阶段末先过三项前置'}, 'patch': body}

    def write(self, lessons, facts_sha, unanswered=()):
        R.write_json(self.home / 'lessons.json', {'schema': R.SCHEMA_REPORT, 'facts_sha256': facts_sha, 'lessons': lessons,
            'reflection': {'went_well': ['盘点很快'], 'went_wrong': ['第三阶段重复构建'], 'summary': '慢在流程不在工具'},
            'unanswered_signals': list(unanswered)})

    def test_facts_find_process_signals_from_existing_records_only(self):
        doc, _ = self.facts()
        kinds = sorted(s['type'] for s in doc['signals'])
        self.assertEqual(kinds, ['dominant_stage', 'long_node', 'repeated_node', 'unrecorded_gap'])
        self.assertTrue(all(s['stage'] == 3 for s in doc['signals']))
        self.assertFalse(any('heartbeat' in s['evidence'] for s in doc['signals']))
        self.assertEqual(R.facts(Path(self.tmp.name) / 'no such game', self.codex)['signals'], [])
        self.assertFalse(doc['usage']['available'])

    def test_complete_reflection_passes_and_renders_report_and_patch_folder(self):
        doc, digest = self.facts()
        self.write([self.lesson(doc['signal_ids'])], digest)
        skill_before = {p: p.read_bytes() for p in self.skill.rglob('*') if p.is_file()}
        result = R.render(self.game, self.skill)
        self.assertTrue(result['passed'], result['findings'])
        self.assertFalse(result['delivery_blocking'])
        page = (self.home / '复盘补丁报告.html').read_text(encoding='utf-8')
        for text in ('自我复盘', '第三阶段没有循环上限', '下次怎么预防', '不增加检查', 'fixture.1', '循环上限'):
            self.assertIn(text, page)
        for name in ('改动文件清单.txt', '改动文件与底本SHA256.txt', '相对已装Skill的差异.patch', '发给英化skill_复盘补丁_复制这段话.txt'):
            self.assertTrue((self.home / 'patch' / name).is_file(), name)
        self.assertEqual(skill_before, {p: p.read_bytes() for p in self.skill.rglob('*') if p.is_file()})

    def reasons(self):
        return ' | '.join(f['where'] + ':' + f['reason'] for f in R.check(self.game, self.skill)['findings'])

    def test_every_signal_must_be_answered(self):
        doc, digest = self.facts()
        self.write([self.lesson(doc['signal_ids'][:1])], digest)
        self.assertIn('没有被任何经验回答', self.reasons())
        self.write([self.lesson(doc['signal_ids'][:1])], digest,
                   [{'signal_id': s, 'reason': '同一根因，已在 L1 回答'} for s in doc['signal_ids'][1:]])
        self.assertTrue(R.check(self.game, self.skill)['passed'])

    def test_reflection_must_have_read_the_real_skill_and_bind_the_current_base(self):
        doc, digest = self.facts()
        lesson = self.lesson(doc['signal_ids']); lesson['skill_analysis']['read_files'] = ['cocos-game-to-english/references/invented.md']
        self.write([lesson], digest); self.assertIn('声称读过的 Skill 文件不存在', self.reasons())
        lesson = self.lesson(doc['signal_ids']); lesson['skill_analysis']['read_files'] = []
        self.write([lesson], digest); self.assertIn('必须先读 Skill', self.reasons())
        lesson = self.lesson(doc['signal_ids']); lesson['patch']['changes'][0]['before_sha256'] = '0' * 64
        self.write([lesson], digest); self.assertIn('补丁底本过期', self.reasons())
        lesson = self.lesson(doc['signal_ids']); lesson['patch']['changes'][0]['path'] = '../outside.md'
        self.write([lesson], digest); self.assertIn('包内的相对路径', self.reasons())
        self.write([self.lesson(doc['signal_ids'])], 'f' * 64); self.assertIn('不是当前这份事实', self.reasons())

    def test_lesson_needs_evidence_prevention_and_may_not_only_add_a_check(self):
        doc, digest = self.facts()
        lesson = self.lesson(doc['signal_ids']); lesson['evidence'] = []
        self.write([lesson], digest); self.assertIn('只能算猜测', self.reasons())
        lesson = self.lesson(doc['signal_ids']); lesson['prevention'] = {}
        self.write([lesson], digest); self.assertIn('第几阶段', self.reasons())
        self.write([self.lesson(doc['signal_ids'], adds_check=True)], digest); self.assertIn('只加一项检查不算吸收经验', self.reasons())
        lesson = self.lesson(doc['signal_ids']); lesson['prevention']['action'] = '任何改动后全量重测一遍'
        self.write([lesson], digest); self.assertIn('blind_full_retest', self.reasons())

    def test_unowned_patch_file_and_unchanged_file_are_refused(self):
        doc, digest = self.facts()
        self.write([self.lesson(doc['signal_ids'])], digest)
        extra = self.home / 'patch/改动文件/remake-core/scripts/extra.py'; extra.parent.mkdir(parents=True); extra.write_text('x=1')
        self.assertIn('没有对应任何一条经验', self.reasons()); extra.unlink()
        rel = 'cocos-game-to-english/references/first-trial-repair.md'
        (self.home / 'patch/改动文件' / rel).write_bytes((self.skill / rel).read_bytes())
        self.assertIn('完全相同', self.reasons())

    def session(self, name, cwd, calls, start=0, parent=None):
        """calls: [(epoch, tokens added, quota percent)] written the way Codex records them (running totals)."""
        iso = lambda t: datetime.datetime.fromtimestamp(t, datetime.timezone.utc).isoformat().replace('+00:00', 'Z')
        rows = [{'timestamp': iso(start), 'type': 'session_meta', 'payload': {'timestamp': iso(start), 'cwd': str(cwd), 'id': name, 'parent_thread_id': parent}}]
        total = 0
        for when, tokens, percent in calls:
            total += tokens
            use = lambda n: {'input_tokens': n * 9 // 10, 'cached_input_tokens': n * 8 // 10, 'output_tokens': n // 10,
                             'reasoning_output_tokens': 0, 'total_tokens': n}
            rows.append({'timestamp': iso(when), 'type': 'event_msg', 'payload': {'type': 'token_count',
                'info': {'total_token_usage': use(total), 'last_token_usage': use(tokens)},
                'rate_limits': {'primary': {'used_percent': percent, 'resets_at': 99, 'window_minutes': 10080}, 'credits': {'balance': '5'}}}})
            rows.append({'timestamp': iso(when), 'type': 'response_item', 'payload': {'type': 'message', 'text': 'not "token_count" data'}})
        path = self.codex / 'sessions/2026/11/14' / (name + '.jsonl')
        path.write_text('\n'.join(json.dumps(r) for r in rows) + '\n', encoding='utf-8')
        return path

    def test_usage_is_split_by_stage_from_this_games_sessions_only(self):
        # stages: 1 [0,600) 2 [600,3600) 3 [3600,12600) 4 [12600,13800) 5 [13800,15000)
        self.session('a', self.game, [(100, 1000, 10.0), (700, 2000, 11.0), (4000, 30000, 14.0), (9000, 50000, 20.0), (20000, 400, 21.0)])
        self.session('b', self.game / 'build', [(5000, 10000, 16.0), (13000, 5000, 20.0)], start=4900)
        self.session('other', Path(self.tmp.name) / 'another game', [(4100, 999999, 15.0)], start=4000)
        self.session('review', Path(self.tmp.name) / 'elsewhere', [(4200, 0, 15.0)], start=4100, parent='a')          # no usage of its own
        self.session('theirs', self.game, [(4300, 777, 15.0)], start=4200, parent='other')                              # spawned by another game
        doc, _ = self.facts()
        used = doc['usage']
        self.assertTrue(used['available']); self.assertEqual(used['sessions'], 3); self.assertEqual(used['subagent_sessions'], 1)
        by = {r['stage']: r for r in used['stages']}
        self.assertEqual([by[n]['total_tokens'] for n in (1, 2, 3, 4, 5)], [1000, 2000, 90000, 5000, 0])
        self.assertEqual([by[n]['calls'] for n in (1, 2, 3, 4, 5)], [1, 1, 3, 1, 0])
        self.assertEqual(by[3]['uncached_tokens'], 90000 // 10 + 90000 // 10)
        self.assertEqual(by[3]['quota_percent_delta'], 9.0)       # 11 before the stage -> 20 at its last reading
        self.assertEqual(by[3]['other_sessions_overlapping'], 2)
        self.assertEqual(by[1]['other_sessions_overlapping'], 0)
        self.assertEqual(used['outside_stages']['total_tokens'], 400)
        self.assertNotIn('quota_percent_delta', by[5])
        signal = [s for s in doc['signals'] if s['type'] == 'usage_dominant']
        self.assertEqual([s['stage'] for s in signal], [3])
        self.write([self.lesson(doc['signal_ids'])], hashlib.sha256((self.home / 'facts.json').read_bytes()).hexdigest())
        R.render(self.game, self.skill)
        page = (self.home / '复盘补丁报告.html').read_text(encoding='utf-8')
        for text in ('各阶段消耗的额度', '9.0万', '+9%', '同时段另有 2 个会话'):
            self.assertIn(text, page)

    def test_restarted_running_total_and_missing_records_do_not_invent_usage(self):
        path = self.session('a', self.game, [(700, 2000, 11.0), (800, 3000, 11.0)])
        rows = path.read_text(encoding='utf-8').splitlines()
        again = json.loads(rows[1]); again['timestamp'] = '1970-01-01T00:15:00Z'      # total restarts at 2000 after a resume
        path.write_text('\n'.join(rows + [json.dumps(again), 'not json "token_count"']) + '\n', encoding='utf-8')
        used = R.facts(self.game, self.codex)['usage']
        self.assertEqual({r['stage']: r['total_tokens'] for r in used['stages']}[2], 7000)
        empty = Path(self.tmp.name) / 'no codex'
        self.assertFalse(R.facts(self.game, empty)['usage']['available'])
        self.assertIn('没有 Codex 会话记录', R.facts(self.game, empty)['usage']['reason'])


if __name__ == '__main__':
    unittest.main()
