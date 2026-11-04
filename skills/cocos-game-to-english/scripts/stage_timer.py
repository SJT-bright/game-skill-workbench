#!/usr/bin/env python3
"""英化阶段用时（10.2.12）：每个阶段、每一步按电脑时钟记下开始和结束；阶段结束、每轮试玩链接、交付时打印用时汇报，
原样发给用户。

Saul 2026-11-01：「能不能在skill放一个阶段用时的汇报，就是自动对应的每一个阶段结束了发一下用时多久，比如修改的一个阶段，
改美工花了多久，第一步英化的美工设计花了多久，等等，全面一点设计」。

记录一行一条，追加在 <工程>/docs/timing/stage-timing.jsonl；汇报每次从记录现算，不靠模型记时间，压缩或重开以后也不丢。
主线程和子进程同时记也不会写坏（用锁文件，不用 fcntl）。只用 Python 标准库，macOS、Windows 都能跑。

  T = python3 stage_timer.py --project <工程>

  T stage <1-5>                       开始第 N 阶段（上一阶段没 done 就先结束它，一起打印它的汇报）
  T done                              结束当前阶段，打印这一阶段的用时汇报
  T begin <步骤> [--who 美术子进程]      开始一步（步骤名见下面 STEPS，也可以用别的大白话名字）
  T end <步骤> [--count 图=26]          这一步做完；同一步做几次就记几次，汇报写次数和总时间
  T link <N>                          发了第 N 轮英文试玩链接，开始等用户试玩；有上一轮时打印上一轮的用时
  T ask <事情>                         问了用户一件要他回答才能往下做的事，开始等他
  T back                              用户回复了（没在等时跑也没关系）
  T mark <事情>                        记一个时间点：中文原版链接、改要求：<几个字>、交付
  T status                            现在开着的阶段和步骤、在不在等用户（压缩或重开以后先跑这个）
  T report [--all]                    当前阶段到现在的用时；--all 打印全程总表并写 docs/timing/timing-report.md

忘了记的，知道时间就加 --at 14:05（今天的时:分）或 --at 2026-11-01T14:05 补上；report、status 加 --at 就按那个时间算。
退出码：0 记下了或打印了；2 用法错（工程不存在、阶段号不对）。写记录出错只警告，退出码照样 0，不挡流程。
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

STAGES = {1: '盘点', 2: '修改', 3: '英文试玩链接', 4: '试玩改进', 5: '全量检查和出包'}
REF_MIN = {1: 30, 2: 90, 3: 20, 5: 90}      # 参考用时（分钟）：超过了提醒一次，不是硬限制
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
        with Lock(path.parent / (path.name + '.lock')):
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
    return '- %s：%s%s' % (name, took, '（%s）' % '，'.join(extra) if extra else '')


class Timeline:
    """从记录还原：阶段（同一个阶段可能进几次，每次一段）、步骤、等用户的时段、时间点、英文链接。步骤、时间点和链接
    都记在它发生时开着的那一段阶段上（没有开着的就记在上一段）。"""

    def __init__(self, events, now, bad=0):
        self.events, self.now, self.bad = events, now, bad
        self.start = events[0]['t'] if events else now
        self.stages, self.steps, self.waits, self.marks, self.links, self.warned = [], [], [], [], [], set()
        self.cur = None
        for e in events:
            try:
                getattr(self, '_on_' + e['ev'], lambda e: None)(e)
            except (KeyError, ValueError, TypeError):
                self.bad += 1

    # ---- 还原 ----
    def entry(self):
        return len(self.stages) - 1

    def _close(self, t):
        idx, st, self.cur = self.entry(), self.cur, None
        st['end'] = t
        for s in self.steps:
            if s['end'] is None and s['entry'] == idx:
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
        if not self.cur and not self.stages:
            self._on_stage({'t': e['t'], 'stage': 1, 'implied': True})
        name = e.get('step') or '?'
        if any(s['name'] == name and s['end'] is None for s in self.steps):
            return
        self.steps.append({'name': name, 'entry': self.entry(), 'start': e['t'], 'end': None, 'auto': False,
                           'who': e.get('who') or '', 'count': {}, 'note': ''})

    def _on_end(self, e):
        name = e.get('step') or '?'
        same = [s for s in self.steps if s['name'] == name]
        opened = [s for s in same if s['end'] is None]
        s = opened[-1] if opened else (same[-1] if same and same[-1]['auto'] else None)
        if s is None:
            return
        s['end'], s['auto'] = e['t'], False
        for k, v in (e.get('count') or {}).items():
            try:
                s['count'][k] = s['count'].get(k, 0) + float(v)
            except (TypeError, ValueError):
                pass
        if e.get('note'):
            s['note'] = e['note']

    def _wait(self, t, what):
        if not self.waiting():
            self.waits.append({'start': t, 'end': None, 'what': what})

    def _on_link(self, e):
        n = int(e['n'])
        self.links.append({'n': n, 't': e['t'], 'entry': self.entry()})
        self._wait(e['t'], '英文试玩链接第 %d 轮' % n)

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

    def end_of(self, st):
        return st['end'] if st['end'] is not None else self.now

    def group(self, steps):
        out = {}
        for s in steps:
            g = out.setdefault(s['name'], {'times': 0, 'sec': 0.0, 'count': {}, 'open': False, 'auto': False,
                                           'first': s['start']})
            g['times'] += 1
            g['sec'] += max(0.0, (s['end'] if s['end'] is not None else self.now) - s['start'])
            g['open'] = g['open'] or s['end'] is None
            g['auto'] = g['auto'] or s['auto']
            for k, v in s['count'].items():
                g['count'][k] = g['count'].get(k, 0) + v
        return sorted(out.items(), key=lambda kv: (kv[1]['first'], ORDER.get(kv[0], len(ORDER))))

    def rounds(self):
        """每个英文链接一轮：play = 这一轮里等用户试玩和回复的时间，fix = 用户等你的时间（到下一个链接为止）。"""
        links = sorted(self.links, key=lambda l: l['t'])
        out = []
        for i, l in enumerate(links):
            nxt = links[i + 1] if i + 1 < len(links) else None
            b = nxt['t'] if nxt else self.now
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
        if wait >= 60:
            head += '，其中等你%s %s' % ('试玩和回复' if st['n'] in (3, 4) else '回复', fmt(wait))
        head += '；从开工算起共 %s' % fmt(b - self.start)
        lines = [head]
        groups = self.group([s for s in self.steps if s['entry'] == idx])
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
        if ref and wall - wait > ref * 60 + 60:
            lines.append('比参考用时 %s多了 %s%s' % (fmt(ref * 60), fmt(wall - wait - ref * 60), NOTE))
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
        groups = self.group([s for s in self.steps if r['link'] <= s['start'] < r['next']])
        lines += [step_line(n, g) for n, g in groups]
        if r['replied'] and r['fix'] > ROUND_REF_MIN * 60 + 60:
            lines.append('从你回复到新链接比参考用时 %s多了 %s%s' % (
                fmt(ROUND_REF_MIN * 60), fmt(r['fix'] - ROUND_REF_MIN * 60), NOTE))
        return '\n'.join(lines)

    def full_report(self):
        deliver = next((m['t'] for m in reversed(self.marks) if m['name'].startswith('交付')), None)
        end = deliver if deliver is not None else self.now
        total, wait = end - self.start, self.wait_in(self.start, end)
        word = '交付' if deliver is not None else '现在'
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
                                                                  fmt(end - s['start']), s['who'] or '主线程',
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
        if not self.cur:
            return None
        st, idx = self.cur, self.entry()
        if st['n'] == 4:
            if self.waiting() or not self.links:
                return None
            last = max(self.links, key=lambda l: l['t'])
            fix = (self.now - last['t']) - self.wait_in(last['t'], self.now)
            key = 'round-%d-%d' % (idx, last['n'])
            if fix > ROUND_REF_MIN * 60 and key not in self.warned:
                return ('提醒：这一轮从用户回复到现在已经 %s，超过参考的 %s。用一句话告诉用户卡在哪、大概还要多久%s。' % (
                    fmt(fix), fmt(ROUND_REF_MIN * 60), NOTE), key)
            return None
        ref = REF_MIN.get(st['n'])
        busy = (self.now - st['start']) - self.wait_in(st['start'], self.now)
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
        tmp = path.with_name(path.name + '.tmp')
        tmp.write_text('\n'.join(parts), encoding='utf-8')
        os.replace(str(tmp), str(path))
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
    common.add_argument('--at', default=argparse.SUPPRESS, help='补记：这件事的时间（14:05、2026-11-01T14:05）')
    p = argparse.ArgumentParser(prog='stage_timer.py', description=__doc__, parents=[common],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', metavar='命令')
    s = sub.add_parser('stage', parents=[common], help='开始第 N 阶段（1-5）')
    s.add_argument('n', type=int, choices=sorted(STAGES))
    sub.add_parser('done', parents=[common], help='结束当前阶段，打印它的用时')
    s = sub.add_parser('begin', parents=[common], help='开始一步')
    s.add_argument('step')
    s.add_argument('--who', default='', help='谁做：美术子进程、代码子进程、文字子进程；主线程不写')
    s = sub.add_parser('end', parents=[common], help='这一步做完')
    s.add_argument('step')
    s.add_argument('--count', action='append', default=[], metavar='名=数', help='做了多少，例如 图=26（可以写几次）')
    s.add_argument('--note', default='', help='一句说明（只写进总表的明细）')
    s = sub.add_parser('link', parents=[common], help='发了第 N 轮英文试玩链接，开始等用户试玩')
    s.add_argument('n', type=int)
    s = sub.add_parser('ask', parents=[common], help='问了用户一件要回答的事，开始等回复')
    s.add_argument('what')
    sub.add_parser('back', parents=[common], help='用户回复了')
    s = sub.add_parser('mark', parents=[common], help='记一个时间点')
    s.add_argument('name')
    sub.add_parser('status', parents=[common], help='现在开着的阶段和步骤')
    s = sub.add_parser('report', parents=[common], help='打印用时；--all 打印全程总表并写 timing-report.md')
    s.add_argument('--all', action='store_true')
    return p


def main(argv=None):
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
    tl = Timeline(events, now, bad)
    out = []

    def record(ev, **fields):
        nonlocal tl
        e = {'t': now, 'at': datetime.fromtimestamp(now).astimezone().isoformat(timespec='seconds'), 'ev': ev}
        e.update({k: v for k, v in fields.items() if v not in (None, '', {}, [])})
        append(project, e)
        e['_i'] = max((x['_i'] for x in events), default=-1) + 1
        events.append(e)
        events.sort(key=lambda x: (x['t'], x['_i']))
        tl = Timeline(events, now, bad)

    def remind():
        r = tl.reminder()
        if r:
            out.append(r[0])
            record('warned', key=r[1])

    if a.cmd == 'stage':
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
        same = next((s for s in tl.steps if s['name'] == a.step and s['end'] is None), None)
        if same:
            out.append('「%s」%s 已经开始了，不用再记。' % (a.step, clock(same['start'])))
        else:
            hint = '' if tl.stages else '（还没跑 stage 1，先按第 1 阶段算）'
            record('begin', step=a.step, who=a.who)
            out.append('记下：%s 开始 %s%s%s' % (clock(now), a.step, '（%s）' % a.who if a.who else '', hint))
        remind()
    elif a.cmd == 'end':
        record('end', step=a.step, count=parse_counts(a.count), note=a.note)
        s = next((s for s in reversed(tl.steps) if s['name'] == a.step and s['end'] == now), None)
        if s:
            out.append('记下：%s 结束 %s，这次用了 %s' % (clock(now), a.step, fmt(s['end'] - s['start'])))
        else:
            out.append('没找到「%s」的开始，这一条没算进用时。下次做这一步前先跑 begin。' % a.step)
        remind()
    elif a.cmd == 'link':
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


if __name__ == '__main__':
    sys.exit(main())
