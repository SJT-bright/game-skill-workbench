#!/usr/bin/env python3
"""英化阶段用时：独立轮次、节点区间和命令实耗；阶段结束、每轮试玩链接、交付时打印用时汇报，
原样发给用户。

Saul 2026-11-01：「能不能在skill放一个阶段用时的汇报，就是自动对应的每一个阶段结束了发一下用时多久，比如修改的一个阶段，
改美工花了多久，第一步英化的美工设计花了多久，等等，全面一点设计」。

记录一行一条，追加在 <工程>/docs/timing/stage-timing.jsonl；汇报每次从记录现算，不靠模型记时间，压缩或重开以后也不丢。
主线程和子进程同时记也不会写坏（用锁文件，不用 fcntl）。只用 Python 标准库，macOS、Windows 都能跑。

  T = python3 stage_timer.py --project <工程>

  T start --run-id <本次ID> --route source|handoff|returned|maintenance  开始独立轮次
  T run [--span-id 节点ID] [--log 文件] [--cwd 目录] <步骤> -- <命令>     自动计命令实耗与退出码
  T pause <原因> / T resume / T abort <原因>                            暂停、恢复、中止
  T publish <Web与Native稳定身份> [--kind chinese]                       仅服务ready后调用，同版去重
  T stage <1-5>                       开始第 N 阶段（上一阶段没 done 就先结束它，一起打印它的汇报）
  T done                              结束当前阶段，打印这一阶段的用时汇报
  T begin <步骤> [--span-id 唯一ID] [--parent-id 父节点] [--who 美术子进程]      开始一步（步骤名见下面 STEPS，也可以用别的大白话名字）
  T end <步骤> [--span-id 对应ID] [--who 执行者] [--count 图=26]          这一步做完；同一步做几次就记几次，汇报写次数和总时间
  T link <N>                          发了第 N 轮英文试玩链接，开始等用户试玩；有上一轮时打印上一轮的用时。
                                      简化.11.9 起英文试玩链接由 serve_preview.py 自动记；同一轮号已经记过就不再记
  T ask <事情>                         问了用户一件要他回答才能往下做的事，开始等他
  T back                              用户回复了（没在等时跑也没关系）
  T mark <事情> [--once]               记一个时间点：中文原版链接、改要求：<几个字>、交付；--once 已经记过同名的就不再记
  T status                            现在开着的阶段和步骤、在不在等用户（压缩或重开以后先跑这个）
  T report [--all]                    当前阶段到现在的用时；--all 打印全程总表并写 docs/timing/timing-report.md

忘了记的，知道时间就加 --at 14:05（今天的时:分）或 --at 2026-11-01T14:05 补上；report、status 加 --at 就按那个时间算。
退出码：run 原样传回命令退出码；其他命令 2 表示用法错。写记录出错只警告 not_recorded，退出码 0 不代表落盘成功。
"""
import argparse
import json
import os
import sys
import time
import uuid
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

STAGES = {1: '盘点', 2: '修改', 3: '英文试玩链接', 4: '试玩改进', 5: '补缺与写包核对'}
# 参考用时（分钟）：超过了提醒一次，不是硬限制。简化.11.9：第 3 阶段先不提醒（10.2.12 定的 20 分只算三项确认，11 起加了中文专项检查、
# 11.3.1 起加了完整美工检查；等第一款按新规矩走完第 3 阶段，用它的实际用时再定，Cocos游戏技能对比分析 11-04 按割草蛋壳特工队查出）
REF_MIN = {1: 30, 2: 90, 5: 90}
ROUND_REF_MIN = 45                           # 第 4 阶段每一轮：从用户回复到下一个链接
STEPS = (                                     # 英化入口「用时汇报」表里的步骤名；汇报按开始先后排，同时开始的按这个顺序
    (1, ('查电脑', '找Cocos', '中文原版导出', '盘点清单')),
    (2, ('英文文字', '美工小样', '美工主要页面', '固定入口', '平台包', '广告诊断', '构建导出')),
    (3, ('构建导出', '导出核对', '中文专项检查', '完整美工检查', '三项确认')),     # 简化.11：中文专项检查（chinese_audit.py）
    (4, ('改问题', '美工其余页面', '广告板块美术', '广告板块', '构建导出', '中文专项检查', '美工复查')),
    (5, ('补记录', '美工证据与交付版本核对', '统一检查', '广告板块验收', '出包')),
    (0, ('重做美术小样', '装环境', '修构建')),             # 0：哪个阶段都可能有
)
ORDER = {name: i for i, name in enumerate(dict.fromkeys(n for _, names in STEPS for n in names))}
LOG = Path('docs') / 'timing' / 'stage-timing.jsonl'
REPORT = Path('docs') / 'timing' / 'timing-report.md'
NOTE = '（参考用时只是提醒，不是硬限制，不为了赶时间少做一步）'


def fmt(sec):
    """秒 -> 「不到 1 分」「18 分」「1 小时 12 分」「2 小时」。"""
    if sec < 60:
        return '不到 1 分'
    m = int(sec / 60 + 0.5)
    if m < 60:
        return '%d 分' % m
    h, m = divmod(m, 60)
    return '%d 小时' % h if m == 0 else '%d 小时 %d 分' % (h, m)


def clock(t):
    return datetime.fromtimestamp(t).strftime('%H:%M')


def num(v):
    return str(int(v)) if float(v).is_integer() else str(v)


def usage(message):
    print('stage_timer.py：' + message, file=sys.stderr)
    sys.exit(2)


def parse_at(text):
    """14:05（今天；比现在晚就是昨天）、2026-11-01T14:05、或秒数 -> 秒数。"""
    s = text.strip()
    try:
        return float(s)
    except ValueError:
        pass
    for pattern in ('%H:%M', '%H:%M:%S'):
        try:
            hm = datetime.strptime(s, pattern)
        except ValueError:
            continue
        d = datetime.now().replace(hour=hm.hour, minute=hm.minute, second=hm.second, microsecond=0)
        if d.timestamp() > time.time() + 60:
            d -= timedelta(days=1)
        return d.timestamp()
    try:
        return datetime.fromisoformat(s).timestamp()
    except ValueError:
        usage('--at 看不懂：%r（写 14:05，或 2026-11-01T14:05）' % text)


class Lock:
    """锁文件（O_EXCL 建文件），macOS、Windows 一样；别的进程死了留下超过 30 秒的锁当作没有。等 10 秒还拿不到就照写：
    每次只追加一行，最坏也只是两行挨着写。"""

    def __init__(self, path, wait=10.0):
        self.path, self.wait, self.fd = str(path), wait, None

    def __enter__(self):
        deadline = time.time() + self.wait
        while True:
            try:
                self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                return self
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(self.path) > 30:
                        os.remove(self.path)
                        continue
                except OSError:
                    pass
                if time.time() > deadline:
                    return self
                time.sleep(0.02)
            except OSError:
                return self

    def __exit__(self, *exc):
        if self.fd is not None:
            os.close(self.fd)
            try:
                os.remove(self.path)
            except OSError:
                pass


def append(project, event):
    path = project / LOG
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with Lock(path.parent / (path.name + '.lock')) as lock:
            if lock.fd is None:
                raise OSError('未取得计时日志写锁；本次不写入')
            with open(path, 'a', encoding='utf-8', newline='\n') as f:
                f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + '\n')
        return True
    except OSError as e:
        print('用时记录没写上（%s）。接着做，汇报里这一段会缺。' % e, file=sys.stderr)
        return False


def load(project):
    """-> (按时间排好的记录, 坏了的行数)。同一时刻的记录按写进去的先后排。"""
    try:
        lines = (project / LOG).read_text(encoding='utf-8', errors='replace').splitlines()
    except OSError:
        return [], 0
    events, bad = [], 0
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            e = json.loads(line)
            e['t'] = float(e['t'])
            if not isinstance(e.get('ev'), str):
                raise ValueError(line)
        except (ValueError, KeyError, TypeError, AttributeError):
            bad += 1
            continue
        e['_i'] = i
        events.append(e)
    events.sort(key=lambda e: (e['t'], e['_i']))
    return events, bad


def step_line(name, g):
    took = fmt(g['sec']) if g['times'] == 1 else '%d 次，共 %s' % (g['times'], fmt(g['sec']))
    if g['open']:
        took = '还在做，到现在 ' + took
    extra = ['%s 张图' % num(v) if k == '图' else '%s %s' % (k, num(v)) for k, v in g['count'].items()]
    if g['auto']:
        extra.append('没记结束，算到阶段结束')
    return '- %s：%s%s；区间实耗 %.3f 秒' % (name, took, '（%s）' % '，'.join(extra) if extra else '', g['sec'])



def merge_intervals(rows):
    out = []
    for a, b in sorted((float(a), float(b)) for a, b in rows if b > a):
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(b, out[-1][1]))
        else:
            out.append((a, b))
    return out


def interval_seconds(rows):
    return sum(b-a for a, b in merge_intervals(rows))


def subtract_intervals(rows, remove):
    out = []
    for a, b in merge_intervals(rows):
        cursor = a
        for x, y in merge_intervals(remove):
            if y <= cursor or x >= b:
                continue
            if x > cursor:
                out.append((cursor, min(x, b)))
            cursor = max(cursor, y)
            if cursor >= b:
                break
        if cursor < b:
            out.append((cursor, b))
    return out


def intersect_intervals(a, b):
    return merge_intervals((max(x, u), min(y, v)) for x, y in a for u, v in b if min(y, v) > max(x, u))


class Timeline:
    """从记录还原：阶段（同一个阶段可能进几次，每次一段）、步骤、等用户的时段、时间点、英文链接。步骤、时间点和链接
    都记在它发生时开着的那一段阶段上（没有开着的就记在上一段）。"""

    def __init__(self, events, now, bad=0, run_id=None):
        self.all_events = events
        starts = [e for e in events if e.get('ev') == 'run_start']
        latest = max(starts, key=lambda e: e.get('_i', e['t']), default=None)
        self.run_id = run_id or (latest.get('run_id') if latest else 'legacy')
        events = [e for e in events if e.get('run_id', 'legacy') == self.run_id]
        self.events, self.now, self.bad = events, now, bad
        self.start = min((e['t'] for e in events), default=now)
        self.stages, self.steps, self.waits, self.marks, self.links, self.warned = [], [], [], [], [], set()
        self.pauses, self.external_waits = [], []
        self.aborted_at, self.abort_reason = None, ''
        self.pending_ends = []
        self.cur = None
        for e in events:
            try:
                getattr(self, '_on_' + e['ev'], lambda e: None)(e)
            except (KeyError, ValueError, TypeError):
                self.bad += 1
        # A system-clock rollback can sort an actual command end before begin.
        # Only an explicit span identity permits recovery; mark wall totals invalid.
        pending, self.pending_ends = self.pending_ends, []
        for e in pending:
            if e.get('span_id') and any(s.get('span_id') == e['span_id'] for s in self.steps):
                self._on_end(e)

    # ---- 还原 ----
    def entry(self):
        return len(self.stages) - 1

    def _close(self, t):
        idx, st, self.cur = self.entry(), self.cur, None
        st['end'] = t
        # A stage boundary is not proof a command or parallel worker finished.
        # Historical untagged events keep their original incomplete boundary.
        for s in self.steps:
            if s['end'] is None and s['entry'] == idx and not s.get('span_id'):
                s['end'], s['auto'] = t, True

    def _on_stage(self, e):
        n = int(e['stage'])
        if self.cur and self.cur['n'] == n:
            self.cur['implied'] = False
            return
        if self.cur:
            self._close(e['t'])
        self.cur = {'n': n, 'start': e['t'], 'end': None, 'implied': bool(e.get('implied'))}
        self.stages.append(self.cur)

    def _on_done(self, e):
        if self.cur:
            self._close(e['t'])

    def _on_begin(self, e):
        if not self.cur:
            self._on_stage({'t': e['t'], 'stage': self.stages[-1]['n'] if self.stages else 1, 'implied': True})
        name, span = e.get('step') or '?', e.get('span_id')
        if any(s['end'] is None and ((span and s.get('span_id') == span) or
               (not span and s['name'] == name and s.get('who', '') == e.get('who', ''))) for s in self.steps):
            return
        self.steps.append({'name': name, 'entry': self.entry(), 'start': e['t'], 'end': None, 'auto': False,
                           'who': e.get('who') or '', 'count': {}, 'note': '', 'span_id': span,
                           'parent_id': e.get('parent_id'), 'node_id': e.get('node_id', name), 'kind': e.get('kind', 'manual'),
                           'state': 'running', 'monotonic_seconds': None, 'exit_code': None, 'clock_discontinuity': False})

    def _on_end(self, e):
        span = e.get('span_id')
        same = [s for s in self.steps if (s.get('span_id') == span if span else s['name'] == e.get('step'))
                and (not e.get('who') or s['who'] == e['who'])]
        opened = [s for s in same if s['end'] is None]
        # Ambiguous old name-only end must not finish a different worker.
        if len(opened) != 1:
            if not same and span:
                self.pending_ends.append(e)
            if not opened and len(same) == 1 and same[0]['auto']:
                same[0]['note'] = '阶段结束后收到迟到结束记录；保留原不完整边界'
            return
        s = opened[0]
        s['end'], s['auto'] = max(s['start'], e['t']), False
        s['state'], s['exit_code'] = e.get('state', 'completed'), e.get('exit_code')
        s['monotonic_seconds'] = e.get('monotonic_seconds')
        s['clock_discontinuity'] = e.get('clock_discontinuity', False)
        for k, v in (e.get('count') or {}).items():
            try:
                s['count'][k] = s['count'].get(k, 0) + float(v)
            except (TypeError, ValueError):
                pass
        if e.get('note'):
            s['note'] = e['note']

    def _on_run_start(self, e):
        pass

    def _on_pause(self, e):
        if not any(p['end'] is None for p in self.pauses):
            self.pauses.append({'start': e['t'], 'end': None, 'reason': e.get('reason', '')})

    def _on_resume(self, e):
        for p in self.pauses:
            if p['end'] is None:
                p['end'] = e['t']

    def _on_external_begin(self, e):
        if not any(p['end'] is None and p['id'] == e['id'] for p in self.external_waits):
            self.external_waits.append({'id': e['id'], 'start': e['t'], 'end': None, 'reason': e.get('reason', '')})

    def _on_external_end(self, e):
        for p in self.external_waits:
            if p['end'] is None and p['id'] == e['id']:
                p['end'] = e['t']

    def _on_abort(self, e):
        self.aborted_at, self.abort_reason = e['t'], e.get('reason', '')
        if self.cur:
            self._close(e['t'])
        for s in self.steps:
            if s['end'] is None:
                s['end'], s['state'], s['auto'] = e['t'], 'interrupted', True

    def _wait(self, t, what):
        if not self.waiting():
            self.waits.append({'start': t, 'end': None, 'what': what})

    def _on_link(self, e):
        n = int(e['n'])
        self.links.append({'n': n, 't': e['t'], 'entry': self.entry(), 'identity': e.get('identity')})
        self._wait(e['t'], '英文试玩链接第 %d 轮' % n)

    def _on_link_identity(self, e):
        for link in self.links:
            if link['n'] == e['n']:
                link['identity'] = e['identity']

    def _on_ask(self, e):
        self._wait(e['t'], e.get('what') or '问题')

    def _on_back(self, e):
        w = self.waiting()
        if w:
            w['end'] = e['t']

    def _on_mark(self, e):
        self.marks.append({'name': e.get('name') or '?', 't': e['t'], 'entry': self.entry()})

    def _on_warned(self, e):
        self.warned.add(e.get('key'))

    # ---- 计算 ----
    def waiting(self):
        return next((w for w in self.waits if w['end'] is None), None)

    def wait_in(self, a, b):
        total = 0.0
        for w in self.waits:
            lo, hi = max(a, w['start']), min(b, w['end'] if w['end'] is not None else self.now)
            total += max(0.0, hi - lo)
        return total

    def run_end(self):
        terminal = [e['t'] for e in self.events if e['ev'] == 'abort' or
                    (e['ev'] == 'mark' and str(e.get('name', '')).startswith('交付'))]
        return max(terminal) if terminal else self.now

    def end_of(self, st):
        return min(st['end'] if st['end'] is not None else self.now, self.run_end())

    def intervals(self, rows, a=None, b=None):
        a = self.start if a is None else a
        b = self.run_end() if b is None else b
        return merge_intervals((max(a, r['start']), min(b, r['end'] if r.get('end') is not None else self.now)) for r in rows)

    def step_seconds(self, s, a=None, b=None):
        lo = max(s['start'], self.start if a is None else a)
        hi = min(s['end'] if s['end'] is not None else self.now, self.run_end() if b is None else b)
        seconds = interval_seconds([(lo, hi)] if s.get('kind') == 'tool' else subtract_intervals([(lo, hi)], self.intervals(self.pauses, lo, hi)))
        if (s.get('monotonic_seconds') is not None and
                (a is None and b is None or (lo <= s['start'] and hi >= s['end']))):
            # A completed subprocess is measured by one monotonic clock; manual
            # spans remain explicit wall intervals rather than pretend CPU time.
            return max(0.0, float(s['monotonic_seconds']))
        return seconds

    def metrics(self):
        end = self.run_end()
        paused = self.intervals(self.pauses)
        completed = [s for s in self.steps if s['end'] is not None and not s['auto']]
        tools = [s for s in completed if s.get('kind') == 'tool']
        tool_intervals = self.intervals(tools)
        manual = [s for s in completed if s.get('kind') != 'tool']
        work = merge_intervals(subtract_intervals(self.intervals(manual), paused) + tool_intervals)
        waits = self.intervals(self.waits)
        external = self.intervals(self.external_waits)
        known = merge_intervals(work + waits + external + paused)
        stages = []
        for idx, stage in enumerate(self.stages):
            a, b = stage['start'], self.end_of(stage)
            interval = [(a, b)]
            seconds = lambda rows: interval_seconds(intersect_intervals(rows, interval))
            stages.append({'entry': idx, 'stage': stage['n'], 'name': STAGES.get(stage['n'], ''),
                           'started_at_epoch': a, 'ended_at_epoch': b, 'open': stage['end'] is None,
                           'wall_seconds': max(0.0, b-a), 'completed_work_interval_union_seconds': seconds(work),
                           'tool_interval_union_seconds': seconds(tool_intervals), 'user_wait_seconds': seconds(waits),
                           'external_wait_seconds': seconds(external), 'paused_seconds': seconds(paused),
                           'unrecorded_seconds': max(0.0, b-a-seconds(known))})
        return {'schema': 'stage-timing-summary.v2', 'run_id': self.run_id,
                'started_at_epoch': self.start, 'ended_at_epoch': end,
                'wall_seconds': max(0.0, end-self.start),
                'completed_work_interval_union_seconds': interval_seconds(work),
                'tool_interval_union_seconds': interval_seconds(tool_intervals),
                'user_wait_seconds': interval_seconds(waits),
                'external_wait_seconds': interval_seconds(external),
                'paused_seconds': interval_seconds(paused),
                'unrecorded_seconds': max(0.0, end-self.start-interval_seconds(known)),
                'user_wait_work_overlap_seconds': interval_seconds(intersect_intervals(work, waits)),
                'aborted': self.aborted_at is not None,
                'wall_interval_totals_valid': not any(s.get('clock_discontinuity') for s in tools),
                'clock_discontinuity_spans': [s.get('span_id') for s in tools if s.get('clock_discontinuity')],
                'open_spans': [s.get('span_id') or s['name'] for s in self.steps if s['end'] is None],
                'stages': stages,
                'steps': [dict(s, seconds=self.step_seconds(s)) for s in self.steps],
                'note': '区间并集不重复累加并行；开放或漏记的区间不当作已完成实耗。工具耗时不是CPU时间。'}

    def group(self, steps, a=None, b=None):
        out = {}
        for s in steps:
            if a is not None and ((s['end'] if s['end'] is not None else self.now) <= a or s['start'] >= b):
                continue
            g = out.setdefault(s['name'], {'times': 0, 'sec': 0.0, 'count': {}, 'open': False, 'auto': False,
                                           'first': s['start']})
            g['times'] += 1
            g['sec'] += self.step_seconds(s, a, b)
            g['open'] = g['open'] or s['end'] is None
            g['auto'] = g['auto'] or s['auto']
            for k, v in (s['count'] if a is None or (s['end'] is not None and a < s['end'] <= b) else {}).items():
                g['count'][k] = g['count'].get(k, 0) + v
        return sorted(out.items(), key=lambda kv: (kv[1]['first'], ORDER.get(kv[0], len(ORDER))))

    def rounds(self):
        """每个英文链接一轮：play = 这一轮里等用户试玩和回复的时间，fix = 用户等你的时间（到下一个链接为止）。"""
        links = sorted(self.links, key=lambda l: l['t'])
        out = []
        for i, l in enumerate(links):
            nxt = links[i + 1] if i + 1 < len(links) else None
            b = nxt['t'] if nxt else self.run_end()
            play = self.wait_in(l['t'], b)
            replied = any(w['end'] is not None and l['t'] <= w['end'] <= b for w in self.waits)
            out.append({'n': l['n'], 'link': l['t'], 'next': nxt['t'] if nxt else None,
                        'next_entry': nxt['entry'] if nxt else None, 'play': play, 'fix': (b - l['t']) - play,
                        'replied': replied})
        return out

    def since_start(self, t):
        return '开工后 %s（%s）' % (fmt(t - self.start), clock(t))

    # ---- 汇报 ----
    def stage_report(self, idx):
        st = self.stages[idx]
        a, b = st['start'], self.end_of(st)
        wall, wait = b - a, self.wait_in(a, b)
        head = '用时｜第 %d 阶段「%s」：%s' % (st['n'], STAGES.get(st['n'], ''), fmt(wall))
        if st['end'] is None:
            head += '，还没结束'
        paused = interval_seconds(self.intervals(self.pauses, a, b))
        if paused:
            head += '，其中暂停 ' + fmt(paused)
        if wait >= 60:
            head += '，其中等你%s %s' % ('试玩和回复' if st['n'] in (3, 4) else '回复', fmt(wait))
        head += '；从开工算起共 %s；本阶段墙钟 %.3f 秒' % (fmt(b - self.start), max(0.0, wall))
        lines = [head]
        groups = self.group(self.steps, a, b)
        lines += [step_line(n, g) for n, g in groups]
        if len(groups) > 1 and sum(g['sec'] for _, g in groups) > wall + 60:
            lines.append('几步是同时做的，加起来比阶段用时长。')
        for m in self.marks:
            if m['entry'] == idx:
                lines.append('- %s：%s' % (m['name'], self.since_start(m['t'])))
        for l in self.links:
            if l['entry'] == idx:
                lines.append('- 英文试玩链接第 %d 轮：%s' % (l['n'], self.since_start(l['t'])))
        if st['n'] == 4:
            back_and_forth = [r for r in self.rounds() if r['next_entry'] == idx and r['replied']]
            if back_and_forth:
                lines.append('- 试玩来回：' + '；'.join('第 %d 轮从你回复到新链接 %s' % (r['n'], fmt(r['fix']))
                                                       for r in back_and_forth))
        ref = REF_MIN.get(st['n'])
        if ref and wall - interval_seconds(merge_intervals(self.intervals(self.pauses, a, b) + self.intervals(self.waits, a, b))) > ref * 60 + 60:
            lines.append('比参考用时 %s多了 %s%s' % (fmt(ref * 60), fmt(wall - interval_seconds(merge_intervals(self.intervals(self.pauses, a, b) + self.intervals(self.waits, a, b))) - ref * 60), NOTE))
        if self.bad:
            lines.append('（记录里有 %d 行坏了，没算进去）' % self.bad)
        return '\n'.join(lines)

    def round_report(self, r):
        if r['replied']:
            head = '用时｜试玩第 %d 轮：你试玩和回复 %s；从你回复到这个新链接 %s' % (r['n'], fmt(r['play']), fmt(r['fix']))
        else:
            head = '用时｜试玩第 %d 轮：你还没回复，先把做好的部分放进新链接（离上一个链接 %s）' % (
                r['n'], fmt(r['next'] - r['link']))
        lines = [head]
        groups = self.group(self.steps, r['link'], r['next'])
        lines += [step_line(n, g) for n, g in groups]
        if r['replied'] and r['fix'] > ROUND_REF_MIN * 60 + 60:
            lines.append('从你回复到新链接比参考用时 %s多了 %s%s' % (
                fmt(ROUND_REF_MIN * 60), fmt(r['fix'] - ROUND_REF_MIN * 60), NOTE))
        return '\n'.join(lines)

    def full_report(self):
        deliver = next((m['t'] for m in reversed(self.marks) if m['name'].startswith('交付')), None)
        end = self.run_end()
        total, wait = end - self.start, self.wait_in(self.start, end)
        word = '交付' if deliver is not None else ('中止' if self.aborted_at is not None else '现在')
        lines = ['用时总表｜开工到%s %s（开工 %s，%s %s）' % (word, fmt(total), clock(self.start), word, clock(end)),
                 ('- 你等我 %s；我等你试玩和回复 %s' % (fmt(total - wait), fmt(wait)) if wait >= 60
                  else '- 你等我 %s；没有等你回复的时间' % fmt(total - wait)),
                 '', '| 阶段 | 用时 | 其中等你试玩和回复 |', '|---|---|---|']
        by_n = {}
        for st in self.stages:
            g = by_n.setdefault(st['n'], {'wall': 0.0, 'wait': 0.0, 'times': 0})
            a, b = st['start'], self.end_of(st)
            g['wall'] += b - a
            g['wait'] += self.wait_in(a, b)
            g['times'] += 1
        for n in sorted(by_n):
            g = by_n[n]
            name = '%d %s' % (n, STAGES.get(n, ''))
            if n == 4 and self.links:
                name += '（试玩 %d 轮）' % len(self.links)
            if g['times'] > 1:
                name += '（进了 %d 次）' % g['times']
            lines.append('| %s | %s | %s |' % (name, fmt(g['wall']), fmt(g['wait']) if g['wait'] >= 60 else '—'))
        lines.append('')
        points = []
        cn = next((m for m in self.marks if m['name'] == '中文原版链接'), None)
        if cn:
            points.append('中文原版链接 开工后 %s' % fmt(cn['t'] - self.start))
        if self.links:
            points.append('第一个英文试玩链接 开工后 %s' % fmt(min(l['t'] for l in self.links) - self.start))
        if deliver is not None:
            points.append('交付 开工后 %s' % fmt(deliver - self.start))
        if points:
            lines.append('- 时间点：' + '；'.join(points))
        fixes = [r for r in self.rounds() if r['next'] is not None and r['replied']]
        if fixes:
            lines.append('- 试玩每轮从你回复到新链接：' + '、'.join(fmt(r['fix']) for r in fixes))
        groups = self.group(self.steps)
        top = sorted(groups, key=lambda kv: -kv[1]['sec'])[:3]
        if top:
            lines.append('- 最花时间的几步：' + '；'.join('%s %s' % (n, fmt(g['sec'])) for n, g in top))
        tail = []
        builds = dict(groups).get('构建导出')
        if builds:
            tail.append('构建导出 %d 次，共 %s' % (builds['times'], fmt(builds['sec'])))
        pictures = sum(g['count'].get('图', 0) for _, g in groups)
        if pictures:
            tail.append('生成图片 %s 张' % num(pictures))
        if tail:
            lines.append('- ' + '；'.join(tail))
        others = [m for m in self.marks if m['name'] != '中文原版链接' and not m['name'].startswith('交付')]
        if others:
            lines.append('- 其他记下的事：' + '；'.join('%s %s' % (clock(m['t']), m['name']) for m in others))
        still = [s['name'] for s in self.steps if s['end'] is None]
        if still:
            lines.append('- 还没记结束的步骤：' + '、'.join(still))
        if self.bad:
            lines.append('（记录里有 %d 行坏了，没算进去）' % self.bad)
        m = self.metrics()
        lines += ['', '- 本轮 ID：' + self.run_id,
                  '- 已完成制作/命令区间并集 %.3f 秒；其中工具区间并集 %.3f 秒；暂停 %.3f 秒；外部等待 %.3f 秒；未记录空档 %.3f 秒。' %
                  (m['completed_work_interval_union_seconds'], m['tool_interval_union_seconds'], m['paused_seconds'], m['external_wait_seconds'], m['unrecorded_seconds']),
                  '- 用户等待与工作可重叠；重叠 %.3f 秒。上面的“你等我”是交付延迟，不是 AI 计算时间。' % m['user_wait_work_overlap_seconds']]
        if m['clock_discontinuity_spans']:
            lines.append('- 工具执行期间系统时钟跳变：只采用节点monotonic实耗；墙钟区间与并集不能作为精确执行总量。')
        if m['aborted']:
            lines.append('- 本轮已中止：' + self.abort_reason + '；未结束步骤不算完成。')
        return '\n'.join(lines)

    def detail_table(self):
        rows = ['| 阶段 | 步骤 | 开始 | 结束 | 用时 | 谁做 | 数量、说明 |', '|---|---|---|---|---|---|---|']
        for s in sorted(self.steps, key=lambda s: s['start']):
            n = self.stages[s['entry']]['n'] if 0 <= s['entry'] < len(self.stages) else '?'
            end = s['end'] if s['end'] is not None else self.now
            info = ['%s %s' % (k, num(v)) for k, v in s['count'].items()] + ([s['note']] if s['note'] else [])
            if s['end'] is None:
                info.append('还没记结束')
            elif s['auto']:
                info.append('没记结束，算到阶段结束')
            rows.append('| %s | %s | %s | %s | %s | %s | %s |' % (n, s['name'], clock(s['start']), clock(end),
                                                                  fmt(self.step_seconds(s)), s['who'] or '主线程',
                                                                  '，'.join(info)))
        for w in self.waits:
            end = w['end'] if w['end'] is not None else self.now
            rows.append('| — | 等回复：%s | %s | %s | %s | 用户 | %s |' % (w['what'], clock(w['start']), clock(end),
                                                                          fmt(end - w['start']),
                                                                          '' if w['end'] is not None else '还在等'))
        return '\n'.join(rows)

    def status(self):
        if not self.events:
            return '还没有用时记录。开工先跑 stage 1。'
        lines = []
        if self.cur:
            st = self.cur
            ref = REF_MIN.get(st['n'])
            lines.append('现在：第 %d 阶段「%s」，已经 %s%s；开工到现在 %s' % (
                st['n'], STAGES.get(st['n'], ''), fmt(self.now - st['start']),
                '（参考 %s以内）' % fmt(ref * 60) if ref else '', fmt(self.now - self.start)))
        elif self.stages:
            lines.append('现在没有开着的阶段（第 %d 阶段已经结束）；开工到现在 %s' % (
                self.stages[-1]['n'], fmt(self.now - self.start)))
        opened = [s for s in self.steps if s['end'] is None]
        lines.append('开着的步骤：' + ('；'.join('%s（%s已经 %s）' % (s['name'], s['who'] + '，' if s['who'] else '',
                                                                  fmt(self.now - s['start'])) for s in opened)
                                    if opened else '没有'))
        lines.append('本轮 ID：' + self.run_id)
        if self.aborted_at is not None:
            lines.append('本轮已中止：' + self.abort_reason)
        for p in self.pauses:
            if p['end'] is None:
                lines.append('当前已暂停：' + p['reason'] + '；暂停期间不算制作实耗。')
        w = self.waiting()
        lines.append('在等回复：' + ('%s，已经 %s' % (w['what'], fmt(self.now - w['start'])) if w else '没有'))
        last = next((e for e in reversed(self.events) if e['ev'] != 'warned'), None)
        if last:
            lines.append('最近一条：%s %s' % (clock(last['t']), describe(last)))
        if self.bad:
            lines.append('（记录里有 %d 行坏了，没算进去）' % self.bad)
        return '\n'.join(lines)

    def reminder(self):
        """-> (提醒的话, key) 或 None：当前阶段（第 4 阶段是当前这一轮）超过参考用时、还没提醒过。"""
        if not self.cur or any(p['end'] is None for p in self.pauses):
            return None
        st, idx = self.cur, self.entry()
        if st['n'] == 4:
            if self.waiting() or any(p['end'] is None for p in self.pauses) or not self.links:
                return None
            last = max(self.links, key=lambda l: l['t'])
            fix = (self.now - last['t']) - self.wait_in(last['t'], self.now)
            key = 'round-%d-%d' % (idx, last['n'])
            if fix > ROUND_REF_MIN * 60 and key not in self.warned:
                return ('提醒：这一轮从用户回复到现在已经 %s，超过参考的 %s。用一句话告诉用户卡在哪、大概还要多久%s。' % (
                    fmt(fix), fmt(ROUND_REF_MIN * 60), NOTE), key)
            return None
        ref = REF_MIN.get(st['n'])
        busy = interval_seconds(subtract_intervals([(st['start'], self.now)], merge_intervals(self.intervals(self.pauses) + self.intervals(self.waits))))
        key = 'stage-%d' % idx
        if ref and busy > ref * 60 and key not in self.warned:
            return ('提醒：第 %d 阶段「%s」已经 %s，超过参考的 %s。用一句话告诉用户卡在哪、大概还要多久%s。' % (
                st['n'], STAGES.get(st['n'], ''), fmt(busy), fmt(ref * 60), NOTE), key)
        return None


def describe(e):
    k = e['ev']
    if k == 'stage':
        return '开始第 %s 阶段' % e.get('stage')
    if k == 'done':
        return '结束阶段'
    if k in ('begin', 'end'):
        return '%s %s' % ('开始' if k == 'begin' else '结束', e.get('step'))
    if k == 'link':
        return '英文试玩链接第 %s 轮' % e.get('n')
    if k == 'ask':
        return '问：%s' % e.get('what')
    if k == 'back':
        return '用户回复了'
    if k == 'mark':
        return str(e.get('name'))
    return k


def write_report(project, tl):
    path = project / REPORT
    parts = ['# 英化用时', '', '记录在 `docs/timing/stage-timing.jsonl`，这一页由 stage_timer.py report --all 写。', '',
             tl.full_report(), '', '## 各阶段', '']
    parts += [tl.stage_report(i) + '\n' for i in range(len(tl.stages))]
    parts += ['## 每一步明细', '', tl.detail_table(), '']
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
        tmp.write_text('\n'.join(parts), encoding='utf-8')
        os.replace(str(tmp), str(path))
        summary = path.with_name('timing-summary.json')
        summary.write_text(json.dumps(tl.metrics(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        run_folder = path.parent / 'runs' / uuid.uuid5(uuid.NAMESPACE_URL, tl.run_id).hex
        run_folder.mkdir(parents=True, exist_ok=True)
        (run_folder/'timing-report.md').write_text(path.read_text(encoding='utf-8'), encoding='utf-8')
        (run_folder/'timing-summary.json').write_text(summary.read_text(encoding='utf-8'), encoding='utf-8')
        return True
    except OSError as e:
        print('总表没写进 %s（%s）' % (path, e), file=sys.stderr)
        return False


def utf8_output():
    """Windows 控制台或管道用的编码写不了中文时换成 UTF-8，免得打印汇报时报错。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            '用时'.encode(stream.encoding or 'ascii')
        except (LookupError, UnicodeEncodeError):
            try:
                stream.reconfigure(encoding='utf-8', errors='replace')
            except (AttributeError, ValueError):
                pass


def parse_counts(items):
    counts = {}
    for item in items:
        k, sep, v = item.replace('＝', '=').partition('=')
        try:
            if not sep or not k.strip():
                raise ValueError(item)
            value = float(v)
        except ValueError:
            print('--count %r 看不懂（写成 图=26），这一项没记。' % item, file=sys.stderr)
            continue
        counts[k.strip()] = int(value) if value.is_integer() else value
    return counts


def parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--project', default=argparse.SUPPRESS, help='游戏工程文件夹（记录写在它的 docs/timing/ 里）')
    common.add_argument('--run-id', default=argparse.SUPPRESS, help='指定本轮任务 ID；省略用最近一次 start')
    common.add_argument('--at', default=argparse.SUPPRESS, help='补记：这件事的时间（14:05、2026-11-01T14:05）')
    p = argparse.ArgumentParser(prog='stage_timer.py', description=__doc__, parents=[common],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', metavar='命令')
    s = sub.add_parser('start', parents=[common], help='开始独立制作/返工轮次；保留历史日志')
    s.add_argument('--route', choices=('source', 'handoff', 'returned', 'maintenance'), default='source')
    s.add_argument('--name', default='')
    s = sub.add_parser('pause', parents=[common], help='明确暂停，不把暂停间隔当工作')
    s.add_argument('reason', nargs='?', default='用户暂停')
    sub.add_parser('resume', parents=[common], help='恢复当前轮次')
    s = sub.add_parser('abort', parents=[common], help='中止当前轮次；未完成步骤保留中断状态')
    s.add_argument('reason', nargs='?', default='已中止')
    s = sub.add_parser('external-begin', parents=[common], help='记录外部排队/额度等待，不冒充工具工作')
    s.add_argument('id'); s.add_argument('reason', nargs='?', default='外部等待')
    s = sub.add_parser('external-end', parents=[common], help='结束指定外部等待')
    s.add_argument('id')
    s = sub.add_parser('publish', parents=[common], help='服务实际ready后按稳定导出身份记录试玩，重开同版去重')
    s.add_argument('identity'); s.add_argument('--kind', choices=('english','chinese'), default='english')
    s = sub.add_parser('run', parents=[common], help='真实命令自动计时，不缓冲进度；退出码原样传回')
    s.add_argument('--span-id'); s.add_argument('--parent-id'); s.add_argument('--who', default='主线程')
    s.add_argument('--cwd'); s.add_argument('--log', type=Path)
    s.add_argument('step'); s.add_argument('command', nargs=argparse.REMAINDER)
    s = sub.add_parser('stage', parents=[common], help='开始第 N 阶段（1-5）')
    s.add_argument('n', type=int, choices=sorted(STAGES))
    sub.add_parser('done', parents=[common], help='结束当前阶段，打印它的用时')
    s = sub.add_parser('begin', parents=[common], help='开始一步')
    s.add_argument('step')
    s.add_argument('--span-id'); s.add_argument('--parent-id')
    s.add_argument('--kind', choices=('manual', 'tool'), default='manual')
    s.add_argument('--who', default='', help='谁做：美术子进程、代码子进程、文字子进程；主线程不写')
    s = sub.add_parser('end', parents=[common], help='这一步做完')
    s.add_argument('step')
    s.add_argument('--span-id'); s.add_argument('--who', default='')
    s.add_argument('--count', action='append', default=[], metavar='名=数', help='做了多少，例如 图=26（可以写几次）')
    s.add_argument('--note', default='', help='一句说明（只写进总表的明细）')
    s = sub.add_parser('link', parents=[common], help='发了第 N 轮英文试玩链接，开始等用户试玩')
    s.add_argument('n', type=int)
    s = sub.add_parser('ask', parents=[common], help='问了用户一件要回答的事，开始等回复')
    s.add_argument('what')
    sub.add_parser('back', parents=[common], help='用户回复了')
    s = sub.add_parser('mark', parents=[common], help='记一个时间点')
    s.add_argument('name')
    s.add_argument('--once', action='store_true', help='已经记过同名的时间点就不再记（serve_preview.py 自动记中文原版链接用）')
    sub.add_parser('status', parents=[common], help='现在开着的阶段和步骤')
    s = sub.add_parser('report', parents=[common], help='打印用时；--all 打印全程总表并写 timing-report.md')
    s.add_argument('--all', action='store_true')
    return p


def _main(argv=None):
    utf8_output()
    a = parser().parse_args(argv)
    if not a.cmd:
        usage('要写命令：stage、done、begin、end、link、ask、back、mark、status、report（见 --help）')
    if not getattr(a, 'project', None):
        usage('要写 --project <游戏工程文件夹>')
    project = Path(a.project).expanduser()
    if not project.is_dir():
        usage('找不到工程文件夹：%s' % project)
    now = parse_at(a.at) if getattr(a, 'at', None) else time.time()
    events, bad = load(project)
    selected_run = getattr(a, 'run_id', None)
    tl = Timeline(events, now, bad, selected_run)
    if selected_run and a.cmd != 'start' and not tl.events:
        usage('没有该 run_id 的记录：' + selected_run)
    out = []

    def record(ev, **fields):
        nonlocal tl
        e = {'schema': 'stage-timing.v2', 'run_id': fields.pop('run_id', tl.run_id), 't': now, 'at': datetime.fromtimestamp(now).astimezone().isoformat(timespec='seconds'), 'ev': ev}
        e.update({k: v for k, v in fields.items() if v not in (None, '', {}, [])})
        if not append(project, e):
            raise TimingWriteFailure('not_recorded：本次用时未落盘，制作继续；不要据此汇报已记下。')
        e['_i'] = max((x['_i'] for x in events), default=-1) + 1
        events.append(e)
        events.sort(key=lambda x: (x['t'], x['_i']))
        tl = Timeline(events, now, bad, selected_run if ev != 'run_start' else e['run_id'])

    def remind():
        r = tl.reminder()
        if r:
            out.append(r[0])
            record('warned', key=r[1])

    # A completed delivery is immutable history. New work starts a fresh run;
    # report/done/old delayed end do not reopen it automatically.
    delivered = any(e['ev'] == 'mark' and str(e.get('name', '')).startswith('交付') for e in tl.events)
    if (delivered or tl.aborted_at is not None) and a.cmd in ('stage', 'begin', 'run'):
        selected_run = uuid.uuid4().hex
        try:
            record('run_start', run_id=selected_run, route='returned', name='交付后返工')
        except TimingWriteFailure as exc:
            if a.cmd == 'run':
                print(str(exc), file=sys.stderr, flush=True)
                return run_command(project, a, selected_run)
            raise
        out.append('已开始独立返工轮次 ' + selected_run + '；上轮耗时保持不变。')

    if a.cmd == 'start':
        rid = selected_run or uuid.uuid4().hex
        if any(e.get('ev') == 'run_start' and e.get('run_id') == rid for e in events):
            print('本轮已经存在：' + rid + '；用 status 查看，不重置历史。')
            return 0
        # Switching an unfinished run without an explicit stop would hide work.
        active = Timeline(events, now, bad)
        active_delivered = any(e['ev'] == 'mark' and str(e.get('name', '')).startswith('交付') for e in active.events)
        if active.run_id != 'legacy' and active.events and not active_delivered and active.aborted_at is None:
            usage('当前轮次尚未交付/中止：' + active.run_id + '；先 resume 继续，或 abort 明确中止后 start')
        selected_run = rid
        record('run_start', run_id=rid, route=a.route, name=a.name)
        out.append('记下：本轮 ' + rid + '，路线 ' + a.route + '；计时与旧轮次分开。')
    elif a.cmd in ('pause', 'resume', 'abort'):
        if a.cmd == 'resume' and not any(p['end'] is None for p in tl.pauses):
            out.append('当前没有暂停，不重复记恢复。')
        elif a.cmd == 'pause' and any(p['end'] is None for p in tl.pauses):
            out.append('当前已暂停，不重复记。')
        else:
            record(a.cmd, reason=getattr(a, 'reason', ''))
            out.append('记下：' + a.cmd + ' ' + getattr(a, 'reason', '') + '；本轮 ' + tl.run_id)
    elif a.cmd in ('external-begin', 'external-end'):
        record(a.cmd.replace('-', '_'), id=a.id, reason=getattr(a, 'reason', ''))
        out.append('记下：' + a.cmd + ' ' + a.id)
    elif a.cmd == 'publish':
        if a.kind == 'chinese':
            if any(e['ev'] == 'mark' and e.get('name') == '中文原版链接' and e.get('identity') == a.identity for e in tl.events):
                out.append('同一份中文导出已就绪，计时不另记。')
            else:
                record('mark', name='中文原版链接', identity=a.identity)
                out.append('记下：中文原版链接已就绪，开工后 ' + fmt(now-tl.start))
        elif any(l.get('identity') == a.identity for l in tl.links):
            out.append('同一份导出已就绪，不算新一轮试玩，用时不另记。')
        else:
            # Bind a manually pre-recorded legacy link, without adding a second
            # round. New automated callers always supply an identity at ready.
            unbound = [l for l in tl.links if not l.get('identity')]
            n = max((l['n'] for l in tl.links), default=0) + 1
            if unbound and unbound[-1] is tl.links[-1]:
                record('link_identity', n=unbound[-1]['n'], identity=a.identity)
                out.append('已给手记第 %d 轮绑定实际导出身份。' % unbound[-1]['n'])
            else:
                record('link', n=n, identity=a.identity)
                previous = next((r for r in tl.rounds() if r['next'] == now), None)
                if previous:
                    out.append(tl.round_report(previous))
                out.append('记下：英文试玩链接第 %d 轮已就绪；本轮 %s。' % (n, tl.run_id))
    elif a.cmd == 'run':
        return run_command(project, a, tl.run_id)
    elif a.cmd == 'stage':
        if tl.cur and tl.cur['n'] == a.n and not tl.cur.get('implied'):
            out.append('第 %d 阶段 %s 已经开始了，不用再记。' % (a.n, clock(tl.cur['start'])))
        else:
            before = tl.entry() if tl.cur and tl.cur['n'] != a.n else None
            record('stage', stage=a.n)
            if before is not None:
                out += [tl.stage_report(before), '（上面是第 %d 阶段的用时，发给用户）' % tl.stages[before]['n'], '']
            out.append('记下：%s 开始第 %d 阶段「%s」' % (clock(now), a.n, STAGES[a.n]))
    elif a.cmd == 'done':
        if tl.cur:
            idx = tl.entry()
            record('done')
            out.append(tl.stage_report(idx))
        elif tl.stages:
            out += ['第 %d 阶段已经结束过，下面是它的用时：' % tl.stages[-1]['n'], tl.stage_report(tl.entry())]
        else:
            out.append('还没开始任何阶段（先跑 stage 1），没有可结束的。')
    elif a.cmd == 'begin':
        same = next((s for s in tl.steps if s['end'] is None and ((a.span_id and s.get('span_id') == a.span_id) or (not a.span_id and s['name'] == a.step and s['who'] == a.who))), None)
        if same:
            out.append('「%s」%s 已经开始了，不用再记。' % (a.step, clock(same['start'])))
        else:
            hint = '' if tl.stages else '（还没跑 stage 1，先按第 1 阶段算）'
            record('begin', step=a.step, who=a.who, span_id=a.span_id or uuid.uuid4().hex, parent_id=a.parent_id, kind=a.kind)
            out.append('记下：%s 开始 %s%s%s' % (clock(now), a.step, '（%s）' % a.who if a.who else '', hint) + '；span=' + str(tl.steps[-1].get('span_id')))
        remind()
    elif a.cmd == 'end':
        matches = [s for s in tl.steps if s['end'] is None and (s.get('span_id') == a.span_id if a.span_id else s['name'] == a.step)
                   and (not a.who or s['who'] == a.who)]
        if len(matches) > 1:
            print('同名步骤有多个执行者，请加 --span-id 或 --who；没有替任一任务记结束。')
            return 2
        record('end', step=a.step, span_id=matches[0].get('span_id') if matches else a.span_id,
               who=a.who, count=parse_counts(a.count), note=a.note)
        s = next((s for s in reversed(tl.steps) if s['name'] == a.step and s['end'] == now), None)
        if s:
            out.append('记下：%s 结束 %s，这次用了 %s' % (clock(now), a.step, fmt(tl.step_seconds(s))) + '；实耗 %.3f 秒；span=%s' % (tl.step_seconds(s), s.get('span_id')))
        else:
            out.append('没找到「%s」的开始，这一条没算进用时。下次做这一步前先跑 begin。' % a.step)
        remind()
    elif a.cmd == 'link':
        if any(l['n'] == a.n for l in tl.links):
            # 简化.11.9: serve_preview.py records links by itself; a manual T link N for the same round is not a second one
            print('第 %d 轮英文试玩链接已经记过（%s），不再记。' % (a.n, clock(next(l['t'] for l in tl.links if l['n'] == a.n))))
            return 0
        record('link', n=a.n)
        r = next((r for r in tl.rounds() if r['next'] == now), None)
        if r:
            out += [tl.round_report(r), '（上面是试玩第 %d 轮的用时，贴在新链接那条回复末尾）' % r['n'], '']
        out.append('记下：%s 发了英文试玩链接第 %d 轮，开始等用户试玩' % (clock(now), a.n))
    elif a.cmd == 'ask':
        record('ask', what=a.what)
        out.append('记下：%s 开始等回复：%s' % (clock(now), a.what))
    elif a.cmd == 'back':
        w = tl.waiting()
        if w:
            record('back')
            out.append('记下：%s 用户回复了（%s），等了 %s' % (clock(now), w['what'], fmt(now - w['start'])))
        else:
            out.append('（没在等回复，不用记）')
    elif a.cmd == 'mark':
        if a.once and any(e.get('ev') == 'mark' and e.get('name') == a.name for e in tl.events):
            print('「%s」已经记过，不再记。' % a.name)
            return 0
        record('mark', name=a.name)
        out.append('记下：%s %s（开工后 %s）' % (clock(now), a.name, fmt(now - tl.start)))
        remind()
    elif a.cmd == 'status':
        out.append(tl.status())
        remind()
    elif a.cmd == 'report':
        if a.all:
            out.append(tl.full_report())
            if write_report(project, tl):
                out.append('（总表也写进了 %s）' % (project / REPORT))
        elif tl.stages:
            out.append(tl.stage_report(tl.entry()))
        else:
            out.append('还没有用时记录。开工先跑 stage 1。')
    print('\n'.join(out))
    return 0



class TimingWriteFailure(Exception):
    pass


def run_command(project, args, run_id):
    """No shell, no retry, no buffered progress. A timer failure never suppresses
    the requested command or changes its return code. Only owned child is stopped.
    """
    command = list(args.command)
    if command and command[0] == '--':
        command = command[1:]
    if not command:
        usage('run 需要在 -- 后提供实际命令及参数')
    if getattr(args, 'at', None):
        usage('run 自动测实际时间，不接受 --at 补记')
    span = (args.span_id + '.' if args.span_id else '') + uuid.uuid4().hex
    def event(ev, **fields):
        now = time.time()
        row = dict(schema='stage-timing.v2', run_id=run_id, t=now,
                   at=datetime.fromtimestamp(now).astimezone().isoformat(timespec='seconds'), ev=ev,
                   span_id=span, node_id=args.span_id or args.step, parent_id=args.parent_id, step=args.step, who=args.who, kind='tool', **fields)
        if not append(project, row):
            print('not_recorded：命令仍执行，计时未落盘。', file=sys.stderr, flush=True)
    wall_started = time.time()
    event('begin', command=command, cwd=str(Path(args.cwd).resolve()) if args.cwd else str(Path.cwd()))
    started = time.monotonic()
    proc = None
    log = None
    code, state, note = 127, 'failed', ''
    print('节点开始｜%s｜span=%s' % (args.step, span), flush=True)
    try:
        if args.log:
            try:
                args.log.parent.mkdir(parents=True, exist_ok=True)
                log = args.log.open('w', encoding='utf-8')
            except OSError as exc:
                print('命令日志未写入，继续执行并实时显示：' + str(exc), file=sys.stderr, flush=True)
        proc = subprocess.Popen(command, cwd=args.cwd, stdout=subprocess.PIPE if log else None,
                                stderr=subprocess.STDOUT if log else None, text=True, encoding='utf-8', errors='replace')
        if log:
            for line in proc.stdout:
                print(line, end='', flush=True)
                try:
                    if log is not None:
                        log.write(line); log.flush()
                except OSError as exc:
                    print('命令日志写入中断，输出继续：' + str(exc), file=sys.stderr, flush=True)
                    try: log.close()
                    except OSError: pass
                    log = None
        code = proc.wait()
        state = 'completed' if code == 0 else 'failed'
    except KeyboardInterrupt:
        code, state, note = 130, 'interrupted', '用户中断命令；未完成'
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill(); proc.wait()
    except OSError as exc:
        note = str(exc)
        print(note, file=sys.stderr, flush=True)
    finally:
        elapsed = time.monotonic() - started
        if log:
            try: log.close()
            except OSError: pass
        if proc is not None and proc.stdout: proc.stdout.close()
        event('end', monotonic_seconds=elapsed, exit_code=code, state=state, note=note,
              clock_discontinuity=abs((time.time()-wall_started)-elapsed) > 2.0,
              log=str(args.log) if args.log else None)
        print('节点结束｜%s｜%.3f 秒｜%s｜exit=%s' % (args.step, elapsed, state, code), flush=True)
    return code


def main(argv=None):
    try:
        return _main(argv)
    except TimingWriteFailure as exc:
        print(str(exc), file=sys.stderr)
        return 0


def begin_observation(project, step, *, node_id=None, parent_id=None):
    """Best-effort in-process observation for services: finish at actual ready,
    not at server shutdown. It never changes a quality decision or executes work.
    """
    project = Path(project)
    rows, bad = load(project)
    now, mono = time.time(), time.monotonic()
    tl = Timeline(rows, now, bad)
    run_id, run_recorded = tl.run_id, True
    if tl.aborted_at is not None or any(e['ev'] == 'mark' and str(e.get('name', '')).startswith('交付') for e in tl.events):
        run_id = uuid.uuid4().hex
        run_recorded = append(project, dict(schema='stage-timing.v2', ev='run_start', run_id=run_id, t=now,
                             at=datetime.fromtimestamp(now).astimezone().isoformat(timespec='seconds'),
                             route='returned', name='交付后试玩服务启动'))
        if not run_recorded:
            print('not_recorded：返工服务的新轮次未落盘，服务继续；不写入旧交付轮次。', file=sys.stderr, flush=True)
    observation = dict(project=str(project), run_id=run_id, span_id=uuid.uuid4().hex,
                       step=step, node_id=node_id or step, parent_id=parent_id,
                       started_epoch=now, started_monotonic=mono, finished=False)
    event = dict(schema='stage-timing.v2', ev='begin', run_id=run_id, t=now,
                 at=datetime.fromtimestamp(now).astimezone().isoformat(timespec='seconds'),
                 step=step, span_id=observation['span_id'], node_id=observation['node_id'],
                 parent_id=parent_id, kind='tool', who='当前进程')
    observation['recorded'] = run_recorded and append(project, event)
    return observation


def finish_observation(observation, *, state='completed', exit_code=0, note=''):
    if not observation or observation.get('finished'):
        return
    observation['finished'] = True
    now = time.time()
    elapsed = max(0.0, time.monotonic()-observation['started_monotonic'])
    event = dict(schema='stage-timing.v2', ev='end', run_id=observation['run_id'], t=now,
                 at=datetime.fromtimestamp(now).astimezone().isoformat(timespec='seconds'),
                 step=observation['step'], span_id=observation['span_id'], kind='tool',
                 state=state, exit_code=exit_code, note=note, monotonic_seconds=elapsed,
                 clock_discontinuity=abs(now-observation['started_epoch']-elapsed)>2.0)
    recorded = observation['recorded'] and append(Path(observation['project']), event)
    if observation['recorded'] and recorded:
        print('节点｜%s｜%.3f 秒｜%s；结束于实际就绪/失败，不累计服务存活时间。' % (observation['step'], elapsed, state), flush=True)
    else:
        print('not_recorded：服务启动用时没有完整落盘，不能作准确统计。', file=sys.stderr, flush=True)


def call(project, *args):
    """For other tools (serve_preview.py): run one command, return what it printed. Never raises: a timing problem is a
    warning line, the caller goes on (用时汇报不挡流程)."""
    import contextlib
    import io
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            main(['--project', str(project)] + [str(a) for a in args])
    except SystemExit as exc:
        if exc.code not in (0, None):
            return '用时没记上（%s）：%s' % (' '.join(map(str, args)), buf.getvalue().strip()[-300:])
    except Exception as exc:  # noqa: BLE001 - timing never stops the link
        return '用时没记上（%s）：%r' % (' '.join(map(str, args)), exc)
    return buf.getvalue().strip()


if __name__ == '__main__':
    sys.exit(main())
