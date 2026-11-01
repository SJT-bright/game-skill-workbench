#!/usr/bin/env python3
"""English pack 10.2.12 (Saul 2026-11-01: a timing report after every stage, with the art and every other step).

stage_timer.py records stages, steps, trial links, waits for the user and time points by the computer clock in
<project>/docs/timing/, and prints the report the session sends: per stage (its steps, how many times, pictures made),
per trial round (the user's play time apart from the time the user waited for the AI) and the whole run at delivery
(also written to timing-report.md). A forgotten done/end is closed at the stage end and named; a stage over its
reference time is pointed out once; parallel writers never break a line; bad lines are skipped; the tool uses the
standard library only and no macOS-only call.
Run: PYTHONDONTWRITEBYTECODE=1 python3 -B test_stage_timer.py
"""
import ast
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE / 'stage_timer.py'
sys.path.insert(0, str(HERE))
import stage_timer as ST  # noqa: E402

T0 = datetime(2026, 11, 1, 9, 0).timestamp()


class Base(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.project = Path(self.td.name) / '游戏 工程'
        self.project.mkdir()

    def T(self, minute, *args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = ST.main(['--project', str(self.project), '--at', str(T0 + minute * 60)] + list(args))
        self.assertEqual(code, 0)
        return buf.getvalue()

    def log(self):
        return (self.project / 'docs' / 'timing' / 'stage-timing.jsonl').read_text(encoding='utf-8').splitlines()


class WholeRun(Base):
    def run_game(self):
        T = self.T
        T(0, 'stage', '1'), T(0, 'begin', '查电脑'), T(2, 'end', '查电脑')
        T(2, 'begin', '中文原版导出'), T(12, 'end', '中文原版导出'), T(12, 'mark', '中文原版链接')
        T(12, 'begin', '盘点清单'), T(20, 'end', '盘点清单')
        self.stage1 = T(20, 'done')
        T(20, 'stage', '2')
        T(20, 'begin', '英文文字', '--who', '文字子进程'), T(20, 'begin', '美工小样', '--who', '美术子进程')
        T(20, 'begin', '固定入口', '--who', '代码子进程'), T(30, 'end', '美工小样', '--count', '图=3')
        T(30, 'begin', '美工主要页面', '--who', '美术子进程'), T(45, 'end', '英文文字'), T(50, 'end', '固定入口')
        T(80, 'end', '美工主要页面', '--count', '图=24')
        T(80, 'begin', '构建导出'), T(82, 'end', '构建导出'), T(85, 'begin', '构建导出'), T(88, 'end', '构建导出')
        self.stage2 = T(90, 'done')
        T(90, 'stage', '3'), T(90, 'begin', '导出核对'), T(91, 'end', '导出核对')
        T(91, 'begin', '三项确认'), T(95, 'end', '三项确认'), T(96, 'link', '1')
        self.stage3 = T(96, 'done')
        T(96, 'stage', '4'), T(96, 'begin', '美工其余页面', '--who', '美术子进程')
        self.back1 = T(130, 'back')
        T(130, 'begin', '改问题'), T(140, 'end', '美工其余页面', '--count', '图=30'), T(145, 'end', '改问题')
        T(146, 'begin', '构建导出'), T(149, 'end', '构建导出')
        self.round1 = T(150, 'link', '2')
        T(170, 'back')
        self.stage4 = T(172, 'done')
        T(172, 'stage', '5'), T(172, 'begin', '补记录'), T(180, 'end', '补记录')
        T(180, 'begin', '统一检查'), T(200, 'end', '统一检查'), T(200, 'begin', '出包'), T(215, 'end', '出包')
        T(216, 'mark', '交付')
        self.stage5 = T(216, 'done')
        self.total = T(216, 'report', '--all')

    def test_each_stage_report_names_its_steps_and_times(self):
        self.run_game()
        self.assertIn('用时｜第 1 阶段「盘点」：20 分', self.stage1)
        for line in ('- 查电脑：2 分', '- 中文原版导出：10 分', '- 盘点清单：8 分', '- 中文原版链接：开工后 12 分（09:12）'):
            self.assertIn(line, self.stage1)
        self.assertIn('用时｜第 2 阶段「修改」：1 小时 10 分；从开工算起共 1 小时 30 分', self.stage2)
        for line in ('- 英文文字：25 分', '- 美工小样：10 分（3 张图）', '- 美工主要页面：50 分（24 张图）',
                     '- 固定入口：30 分', '- 构建导出：2 次，共 5 分', '几步是同时做的'):
            self.assertIn(line, self.stage2)
        self.assertLess(self.stage2.index('美工小样'), self.stage2.index('美工主要页面'))   # in the order they began
        self.assertLess(self.stage2.index('美工主要页面'), self.stage2.index('构建导出'))
        self.assertIn('- 英文试玩链接第 1 轮：开工后 1 小时 36 分（10:36）', self.stage3)
        self.assertNotIn('英文试玩链接第 1 轮', self.stage4)                                # it belongs to stage 3
        self.assertIn('其中等你试玩和回复 54 分', self.stage4)
        self.assertIn('- 试玩来回：第 1 轮从你回复到新链接 20 分', self.stage4)
        self.assertIn('- 交付：开工后 3 小时 36 分（12:36）', self.stage5)
        self.assertNotIn('参考用时', self.stage2)                                           # 70 min < 90 min

    def test_each_trial_round_separates_play_time_from_waiting_for_the_ai(self):
        self.run_game()
        self.assertIn('等了 34 分', self.back1)
        self.assertIn('用时｜试玩第 1 轮：你试玩和回复 34 分；从你回复到这个新链接 20 分', self.round1)
        for line in ('- 美工其余页面：44 分（30 张图）', '- 改问题：15 分', '- 构建导出：3 分', '贴在新链接那条回复末尾'):
            self.assertIn(line, self.round1)

    def test_whole_run_table_and_file(self):
        self.run_game()
        for line in ('用时总表｜开工到交付 3 小时 36 分（开工 09:00，交付 12:36）',
                     '- 你等我 2 小时 42 分；我等你试玩和回复 54 分',
                     '| 4 试玩改进（试玩 2 轮） | 1 小时 16 分 | 54 分 |', '| 2 修改 | 1 小时 10 分 | — |',
                     '- 时间点：中文原版链接 开工后 12 分；第一个英文试玩链接 开工后 1 小时 36 分；交付 开工后 3 小时 36 分',
                     '- 试玩每轮从你回复到新链接：20 分', '- 最花时间的几步：美工主要页面 50 分；美工其余页面 44 分；固定入口 30 分',
                     '- 构建导出 3 次，共 8 分；生成图片 57 张'):
            self.assertIn(line, self.total)
        md = (self.project / 'docs' / 'timing' / 'timing-report.md').read_text(encoding='utf-8')
        for part in ('# 英化用时', '用时总表｜开工到交付', '## 各阶段', '用时｜第 5 阶段', '## 每一步明细',
                     '| 2 | 美工主要页面 | 09:30 | 10:20 | 50 分 | 美术子进程 | 图 24 |', '| — | 等回复：英文试玩链接第 1 轮 |'):
            self.assertIn(part, md)
        for line in self.log():                        # every line is one JSON record with the clock time
            e = json.loads(line)
            self.assertIn('at', e)
            self.assertIsInstance(e['t'], float)


class ForgottenSteps(Base):
    def test_forgotten_done_is_closed_by_the_next_stage(self):
        self.T(0, 'stage', '1')
        self.T(0, 'begin', '查电脑')
        out = self.T(10, 'stage', '2')
        self.assertIn('用时｜第 1 阶段「盘点」：10 分', out)
        self.assertIn('- 查电脑：10 分（没记结束，算到阶段结束）', out)
        self.assertIn('上面是第 1 阶段的用时，发给用户', out)
        self.assertIn('记下：09:10 开始第 2 阶段「修改」', out)
        out = self.T(12, 'end', '查电脑')                  # a late end still lands on the step
        self.assertIn('这次用了 12 分', out)

    def test_end_without_begin_and_double_begin_are_harmless(self):
        self.T(0, 'stage', '2')
        self.assertIn('没找到「英文文字」的开始', self.T(5, 'end', '英文文字'))
        self.T(6, 'begin', '固定入口')
        self.assertIn('已经开始了，不用再记', self.T(7, 'begin', '固定入口'))
        self.assertIn('已经开始了，不用再记', self.T(7, 'stage', '2'))
        self.assertIn('没在等回复', self.T(8, 'back'))
        self.assertIn('- 固定入口：还在做，到现在 4 分', self.T(10, 'report'))

    def test_begin_before_stage_one_counts_as_stage_one(self):
        self.assertIn('先按第 1 阶段算', self.T(0, 'begin', '查电脑'))
        self.T(1, 'stage', '1')
        self.T(3, 'end', '查电脑')
        out = self.T(5, 'done')
        self.assertIn('用时｜第 1 阶段「盘点」：5 分', out)
        self.assertNotIn('（进了', self.T(5, 'report', '--all'))

    def test_question_wait_is_apart(self):
        self.T(0, 'stage', '1')
        self.T(1, 'ask', '能不能装 Cocos 2.4.3')
        self.assertIn('等了 20 分', self.T(21, 'back'))
        out = self.T(30, 'done')
        self.assertIn('用时｜第 1 阶段「盘点」：30 分，其中等你回复 20 分', out)
        self.assertNotIn('参考用时', out)                    # 10 min of work, the wait does not count

    def test_status_after_compaction(self):
        self.T(0, 'stage', '2')
        self.T(0, 'begin', '美工主要页面', '--who', '美术子进程')
        out = self.T(31, 'status')
        self.assertIn('现在：第 2 阶段「修改」，已经 31 分（参考 1 小时 30 分以内）', out)
        self.assertIn('开着的步骤：美工主要页面（美术子进程，已经 31 分）', out)
        self.assertIn('在等回复：没有', out)
        self.assertIn('最近一条：09:00 开始 美工主要页面', out)


class Reminders(Base):
    def test_a_stage_over_its_reference_is_pointed_out_once(self):
        self.T(0, 'stage', '3')
        self.T(0, 'begin', '三项确认')
        out = self.T(25, 'end', '三项确认')
        self.assertIn('提醒：第 3 阶段「英文试玩链接」已经 25 分，超过参考的 20 分', out)
        self.assertIn('不为了赶时间少做一步', out)
        self.T(26, 'begin', '导出核对')
        self.assertNotIn('提醒', self.T(27, 'end', '导出核对'))
        self.assertIn('比参考用时 20 分多了 7 分', self.T(27, 'done'))

    def test_a_slow_trial_round_is_pointed_out(self):
        self.T(0, 'stage', '4')
        self.T(0, 'link', '1')
        self.assertNotIn('提醒', self.T(60, 'status'))     # the user is playing: no reminder
        self.T(60, 'back')
        self.T(61, 'begin', '改问题')
        out = self.T(110, 'end', '改问题')
        self.assertIn('提醒：这一轮从用户回复到现在已经 50 分，超过参考的 45 分', out)
        out = self.T(112, 'link', '2')
        self.assertIn('从你回复到这个新链接 52 分', out)
        self.assertIn('从你回复到新链接比参考用时 45 分多了 7 分', out)

    def test_a_link_before_the_reply_says_so(self):
        self.T(0, 'stage', '4')
        self.T(0, 'link', '1')
        out = self.T(30, 'link', '2')
        self.assertIn('用时｜试玩第 1 轮：你还没回复，先把做好的部分放进新链接（离上一个链接 30 分）', out)


class Robustness(Base):
    def test_bad_lines_are_skipped(self):
        self.T(0, 'stage', '1')
        with open(self.project / 'docs' / 'timing' / 'stage-timing.jsonl', 'a', encoding='utf-8') as f:
            f.write('{broken\n["not", "a", "record"]\n{"t": 1, "ev": "stage"}\n')
        self.T(5, 'begin', '查电脑')
        out = self.T(9, 'report')
        self.assertIn('- 查电脑：还在做，到现在 4 分', out)
        self.assertIn('记录里有 3 行坏了，没算进去', out)

    def test_backfilled_event_slots_in_by_time(self):
        self.T(10, 'stage', '2')
        self.T(0, 'stage', '1')                            # remembered later: stage 1 began at 09:00
        out = self.T(20, 'report', '--all')
        self.assertIn('| 1 盘点 | 10 分 | — |', out)
        self.assertIn('| 2 修改 | 10 分 | — |', out)

    def test_parallel_writers_keep_every_line(self):
        code = ('import sys; sys.path.insert(0, %r); import stage_timer as S\n'
                'for i in range(15): S.main(["--project", sys.argv[1], "begin", "w%%s-%%d" %% (sys.argv[2], i)])\n'
                % str(HERE))
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8')
        procs = [subprocess.Popen([sys.executable, '-B', '-c', code, str(self.project), str(k)], env=env,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) for k in range(6)]
        for p in procs:
            _, err = p.communicate(timeout=120)
            self.assertEqual(p.returncode, 0, err.decode('utf-8', 'replace')[-500:])
        lines = self.log()
        self.assertEqual(len(lines), 90)
        steps = {json.loads(l)['step'] for l in lines}
        self.assertEqual(len(steps), 90)
        self.assertFalse((self.project / 'docs' / 'timing' / 'stage-timing.jsonl.lock').exists())

    def test_stale_lock_is_ignored(self):
        lock = self.project / 'docs' / 'timing' / 'stage-timing.jsonl.lock'
        lock.parent.mkdir(parents=True)
        lock.write_text('')
        old = time.time() - 120
        os.utime(lock, (old, old))
        started = time.time()
        self.T(0, 'stage', '1')
        self.assertLess(time.time() - started, 5)
        self.assertEqual(len(self.log()), 1)

    def test_cli_help_and_usage_errors(self):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8')

        def run(*args):
            return subprocess.run([sys.executable, '-B', str(TOOL)] + list(args), capture_output=True, text=True,
                                  encoding='utf-8', env=env)
        r = run('--help')
        self.assertEqual(r.returncode, 0, r.stderr)
        for word in ('stage', 'done', 'begin', 'end', 'link', 'ask', 'back', 'mark', 'status', 'report'):
            self.assertIn(word, r.stdout)
        self.assertEqual(run('--project', str(self.project), 'stage', '9').returncode, 2)
        self.assertEqual(run('--project', str(self.project / 'nope'), 'stage', '1').returncode, 2)
        self.assertEqual(run('stage', '1').returncode, 2)
        r = run('stage', '1', '--project', str(self.project))               # options after the command work too
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('开始第 1 阶段', r.stdout)
        r = run('--project', str(self.project), 'end', '查电脑', '--count', 'abc')
        self.assertEqual(r.returncode, 0)
        self.assertIn('看不懂', r.stderr)

    def test_clock_and_iso_times(self):
        t = ST.parse_at('2026-11-01T14:05')
        self.assertEqual(datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M'), '2026-11-01 14:05')
        t = ST.parse_at('00:00')
        self.assertLessEqual(t, time.time() + 60)
        self.assertEqual(datetime.fromtimestamp(t).strftime('%H:%M'), '00:00')
        self.assertEqual(ST.parse_at('100.5'), 100.5)

    def test_durations_read_plainly(self):
        self.assertEqual(ST.fmt(30), '不到 1 分')
        self.assertEqual(ST.fmt(18 * 60), '18 分')
        self.assertEqual(ST.fmt(72 * 60), '1 小时 12 分')
        self.assertEqual(ST.fmt(120 * 60 + 10), '2 小时')

    def test_standard_library_only_and_no_mac_only_call(self):
        src = TOOL.read_text(encoding='utf-8')
        tree = ast.parse(src)
        names = {a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        names |= {n.module.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
        self.assertLessEqual(names, {'argparse', 'json', 'os', 'sys', 'time', 'datetime', 'pathlib'})
        for gone in ('fcntl', '/usr/bin/python3', 'pgrep', 'cp -c', 'open -R'):
            self.assertNotIn(gone, src.split('"""', 2)[2], gone)


if __name__ == '__main__':
    unittest.main()
