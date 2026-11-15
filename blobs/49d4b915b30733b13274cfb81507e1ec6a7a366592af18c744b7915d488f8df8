#!/usr/bin/env python3
"""Post-delivery retrospective patch report.

facts   read this game's existing timing / issue / experience records (no game, browser or check is run)
usage   per-stage model usage and quota read from Codex's own local session records
check   validate the agent's written reflection and its Skill patch against the installed Skill
render  write the readable report and a hand-over patch folder

Nothing here installs, edits or publishes a Skill, and no result decides whether a game may be delivered.
"""
import argparse
import datetime
import difflib
import hashlib
import html
import json
import os
import re
import sys
from pathlib import Path

SCHEMA_FACTS = 'retrospective_facts.v1'
SCHEMA_REPORT = 'retrospective_patch_report.v1'
OUT = 'docs/production-learning/retrospective'
LONG_NODE_SECONDS = 60 * 60
GAP_SECONDS = 30 * 60
REPEAT_TIMES = 3
DOMINANT_SHARE = 0.40
MAX_BYTES = 4 * 1024 * 1024
MAX_SESSION_FILES = 2000
MAX_OTHER_SESSIONS = 300
STAMP = re.compile(r'"timestamp"\s*:\s*"([^"]+)"')
TOKEN_KEYS = ('input_tokens', 'cached_input_tokens', 'output_tokens', 'reasoning_output_tokens', 'total_tokens')
KINDS = ('process', 'tool', 'rule_gap', 'project_only')
DECISIONS = ('change_skill', 'project_only', 'no_change')
STAGE_NAMES = {1: '盘点', 2: '修改', 3: '英文试玩', 4: '试玩改进', 5: '补缺与出包'}
# Behaviours the owner revoked for good (production-learning-policy.json); a lesson may not bring them back.
REVOKED_WORDS = {
    'full_art_receipt': ('完整美术回执', '完整美工回执', 'full_art_receipt'),
    'default_video_recording': ('默认录屏', '全部录屏', 'default_video_recording'),
    'blind_full_retest': ('全量重测', '全部重测', '全矩阵重跑', 'blind_full_retest'),
    'alternate_writer': ('另一条写包', '备用写包', 'alternate_writer'),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, OSError):
        return None


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return path


def clock(seconds):
    seconds = int(round(max(0.0, float(seconds or 0))))
    return '%d:%02d:%02d' % (seconds // 3600, seconds % 3600 // 60, seconds % 60)


def default_skill_root():
    return Path(__file__).resolve().parents[2]


def skill_base(root):
    doc = read_json(Path(root) / 'cocos-game-to-english' / 'PROVENANCE.json') or {}
    return {'revision': str(doc.get('revision') or 'unknown')}


def inside(root, rel):
    """A Skill-relative path that stays inside the Skill root; None otherwise."""
    if not isinstance(rel, str) or not rel or rel.startswith(('/', '\\')) or ':' in rel:
        return None
    parts = Path(rel.replace('\\', '/')).parts
    if any(p in ('..', '.') for p in parts):
        return None
    return Path(root).joinpath(*parts)


# ---------------------------------------------------------------- usage (Codex local session records)

def amount(n):
    n = float(n or 0)
    if n >= 1e8:
        return '%.2f亿' % (n / 1e8)
    if n >= 1e4:
        return '%.1f万' % (n / 1e4)
    return '%d' % n


def codex_home(value=None):
    return Path(value or os.environ.get('CODEX_HOME') or (Path.home() / '.codex'))


def epoch(text):
    try:
        return datetime.datetime.fromisoformat(str(text).replace('Z', '+00:00')).timestamp()
    except (TypeError, ValueError):
        return None


def same_place(cwd, project):
    try:
        a, b = os.path.normcase(os.path.realpath(str(cwd))), os.path.normcase(os.path.realpath(str(project)))
    except (OSError, ValueError):
        return False
    return a == b or a.startswith(b.rstrip('/\\') + os.sep)


def session_events(path):
    """(session start, cwd, [(time, usage delta, quota)]) from one session file; only usage lines are parsed."""
    start = cwd = None
    events, previous = [], None
    try:
        with open(path, encoding='utf-8', errors='replace') as stream:
            for n, line in enumerate(stream):
                if n == 0:
                    try:
                        meta = json.loads(line).get('payload') or {}
                    except ValueError:
                        return None, None, []
                    start, cwd = epoch(meta.get('timestamp')), meta.get('cwd')
                    continue
                if '"token_count"' not in line:
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                payload = row.get('payload') if isinstance(row.get('payload'), dict) else {}
                when = epoch(row.get('timestamp'))
                if payload.get('type') != 'token_count' or when is None:
                    continue
                info = payload.get('info') if isinstance(payload.get('info'), dict) else {}
                total = info.get('total_token_usage') if isinstance(info.get('total_token_usage'), dict) else None
                delta = None
                if total is not None:
                    current = {k: int(total.get(k) or 0) for k in TOKEN_KEYS}
                    if previous is not None and current['total_tokens'] >= previous['total_tokens']:
                        delta = {k: current[k] - previous[k] for k in TOKEN_KEYS}
                    else:  # first record of the file, or the running total restarted
                        last = info.get('last_token_usage') if isinstance(info.get('last_token_usage'), dict) else current
                        delta = {k: int(last.get(k) or 0) for k in TOKEN_KEYS}
                    previous = current
                limits = payload.get('rate_limits') if isinstance(payload.get('rate_limits'), dict) else {}
                primary = limits.get('primary') if isinstance(limits.get('primary'), dict) else {}
                credits = limits.get('credits') if isinstance(limits.get('credits'), dict) else {}
                quota = {'percent': primary.get('used_percent'), 'resets_at': primary.get('resets_at'),
                         'window_minutes': primary.get('window_minutes'), 'balance': credits.get('balance')}
                events.append((when, delta if delta and delta['total_tokens'] > 0 else None, quota))
    except OSError:
        return None, None, []
    return start, cwd, events


def call_times(path, lo, hi):
    """Times of another session's model calls inside [lo, hi); nothing else of that session is read."""
    out = []
    try:
        with open(path, encoding='utf-8', errors='replace') as stream:
            for line in stream:
                if '"token_count"' in line:
                    found = STAMP.search(line[:200])
                    when = epoch(found.group(1)) if found else None
                    if when is not None and lo <= when < hi:
                        out.append(when)
    except OSError:
        pass
    return out


def usage(project, windows, home=None):
    """Per-stage usage of this game's own Codex sessions. windows: [{'stage','entry','start','end'}]."""
    project = Path(project).resolve()
    root = codex_home(home)
    out = {'source': 'codex_local_sessions', 'available': False, 'stages': [], 'sessions': 0,
           'boundary': '用量只统计工作目录是本作的 Codex 会话，是准确值；周额度百分比是整个账号的，同时段有其他会话时会一并上涨，只作参考。'}
    folders = [d for d in (root / 'sessions', root / 'archived_sessions') if d.is_dir()]
    if not folders:
        out['reason'] = '这台电脑上没有 Codex 会话记录；不是 Codex 制作或换过电脑时没有额度数据'
        return out
    lo = min((w['start'] for w in windows), default=None)
    hi = max((w['end'] for w in windows), default=None)
    candidates = []
    for folder in folders:
        for path in folder.rglob('*.jsonl'):
            try:
                if path.is_file() and (lo is None or path.stat().st_mtime >= lo - 60):
                    candidates.append(path)
            except OSError:
                continue
    candidates = sorted(candidates)[-MAX_SESSION_FILES:]
    mine, others, metas = [], [], []
    for path in candidates:
        try:
            with open(path, encoding='utf-8', errors='replace') as stream:
                meta = (json.loads(stream.readline()).get('payload') or {})
        except (OSError, ValueError, AttributeError):
            continue
        start = epoch(meta.get('timestamp'))
        if start is None or (hi is not None and start > hi):
            continue
        metas.append({'id': meta.get('id'), 'parent': meta.get('parent_thread_id'), 'start': start, 'path': path,
                      'here': same_place(meta.get('cwd') or '', project)})
    # A sub-agent or approval-review session belongs to the session that spawned it, wherever its own cwd is.
    known = {m['id'] for m in metas if m['id']}
    owned = {m['id'] for m in metas if m['here'] and m['parent'] not in known}
    grew = True
    while grew:
        grew = False
        for m in metas:
            if m['id'] not in owned and m['parent'] in owned:
                owned.add(m['id']); grew = True
    for m in metas:
        if m['id'] in owned or (m['here'] and not m['id']):
            mine.append(m['path'])
            out['subagent_sessions'] = out.get('subagent_sessions', 0) + (1 if m['parent'] in owned else 0)
        else:
            others.append((m['start'], m['path'].stat().st_mtime, m['path']))
    events = []
    for path in mine:
        events.extend(session_events(path)[2])
    events.sort(key=lambda e: e[0])
    out['sessions'] = len(mine)
    if not events:
        out['reason'] = '没有找到工作目录是本作的 Codex 会话记录'
        return out
    busy = []
    if lo is not None:
        overlapping = sorted((x for x in others if x[0] < hi and x[1] > lo), key=lambda x: x[1])
        out['other_sessions_scanned'], out['other_sessions_skipped'] = min(len(overlapping), MAX_OTHER_SESSIONS), max(0, len(overlapping) - MAX_OTHER_SESSIONS)
        busy = [t for t in (call_times(x[2], lo, hi) for x in overlapping[-MAX_OTHER_SESSIONS:]) if t]
    blank = lambda: dict({k: 0 for k in TOKEN_KEYS}, calls=0)
    rows = [dict(blank(), stage=w['stage'], entry=w.get('entry'), _w=w, _quota=[]) for w in windows]
    outside, before = blank(), {}
    for when, delta, quota in events:
        row = next((r for r in rows if r['_w']['start'] <= when < r['_w']['end']), None)
        target = row if row is not None else outside
        if delta:
            target['calls'] += 1
            for k in TOKEN_KEYS:
                target[k] += delta[k]
        if quota.get('percent') is not None:
            if row is not None:
                row['_quota'].append(quota)
            for r in rows:
                if when < r['_w']['start']:
                    before[id(r)] = quota  # last reading seen before that stage began
    total = sum(r['total_tokens'] for r in rows) or 0
    for r in rows:
        w, readings = r.pop('_w'), r.pop('_quota')
        r['uncached_tokens'] = max(0, r['input_tokens'] - r['cached_input_tokens']) + r['output_tokens']
        r['share'] = round(r['total_tokens'] / total, 4) if total else 0.0
        r['other_sessions_overlapping'] = sum(1 for times in busy if any(w['start'] <= t < w['end'] for t in times))
        if readings:
            first = before.get(id(r)) or readings[0]
            last = readings[-1]
            if first.get('resets_at') == last.get('resets_at'):
                r['quota_percent_delta'] = round(float(last['percent']) - float(first['percent']), 1)
            else:
                r['quota_note'] = '额度周期在这个阶段内重置，百分比无法相减'
            r['quota_percent_end'] = last['percent']
            if first.get('balance') not in (None, last.get('balance')):
                try:
                    r['credits_spent'] = round(float(first['balance']) - float(last['balance']), 4)
                except (TypeError, ValueError):
                    pass
        out['stages'].append(r)
    out['available'] = True
    out['total_tokens'] = total
    out['outside_stages'] = dict(outside, uncached_tokens=max(0, outside['input_tokens'] - outside['cached_input_tokens']) + outside['output_tokens'])
    return out


def stage_windows(project):
    summary = read_json(Path(project).resolve() / 'docs/timing/timing-summary.json')
    rows = summary.get('stages') if isinstance(summary, dict) and isinstance(summary.get('stages'), list) else []
    return [{'stage': r['stage'], 'entry': r.get('entry'), 'start': float(r['started_at_epoch']), 'end': float(r['ended_at_epoch'])}
            for r in rows if isinstance(r, dict) and isinstance(r.get('stage'), int)
            and isinstance(r.get('started_at_epoch'), (int, float)) and isinstance(r.get('ended_at_epoch'), (int, float))]


# ---------------------------------------------------------------- facts

def stage_of(step, stages):
    start = step.get('start')
    for row in stages:
        if start is not None and row['started_at_epoch'] <= start < row['ended_at_epoch']:
            return row['stage']
    return None


def facts(project, home=None):
    project = Path(project).resolve()
    summary = read_json(project / 'docs/timing/timing-summary.json')
    out = {'schema': SCHEMA_FACTS, 'sources': [], 'stages': [], 'signals': [], 'issues': [], 'experience_bundles': [],
           'boundary': '只读取本作已有记录；不运行游戏、浏览器或检查。信号是需要复盘回答的问题，不是结论。'}
    signals = out['signals']
    if isinstance(summary, dict) and isinstance(summary.get('stages'), list):
        out['sources'].append('docs/timing/timing-summary.json')
        rows = [r for r in summary['stages'] if isinstance(r, dict) and isinstance(r.get('stage'), int)]
        total_work = sum(float(r.get('completed_work_interval_union_seconds') or 0) for r in rows) or 0.0
        total_wall = sum(float(r.get('wall_seconds') or 0) for r in rows) or 0.0
        for r in rows:
            work = float(r.get('completed_work_interval_union_seconds') or 0)
            wall = float(r.get('wall_seconds') or 0)
            wait = sum(float(r.get(k) or 0) for k in ('user_wait_seconds', 'external_wait_seconds', 'paused_seconds'))
            gap = float(r.get('unrecorded_seconds') or 0)
            share = (work / total_work) if total_work else ((wall / total_wall) if total_wall else 0.0)
            out['stages'].append({'stage': r['stage'], 'entry': r.get('entry'), 'name': STAGE_NAMES.get(r['stage'], ''),
                                  'wall_seconds': wall, 'work_seconds': work, 'wait_seconds': wait,
                                  'unrecorded_seconds': gap, 'share': round(share, 4)})
            tag = 'S%d.%s' % (r['stage'], r.get('entry', 0))
            if share >= DOMINANT_SHARE and len(rows) > 1:
                signals.append({'id': tag + '.dominant', 'type': 'dominant_stage', 'stage': r['stage'],
                                'evidence': '第 %d 阶段占全程 %d%%（%s）' % (r['stage'], round(share * 100), clock(work or wall))})
            if gap >= GAP_SECONDS:
                signals.append({'id': tag + '.gap', 'type': 'unrecorded_gap', 'stage': r['stage'],
                                'evidence': '第 %d 阶段有 %s 没有任何节点记录' % (r['stage'], clock(gap))})
        steps = [s for s in summary.get('steps') or [] if isinstance(s, dict) and not s.get('auto')]
        repeats = {}
        for s in steps:
            stage = stage_of(s, [r for r in rows if 'started_at_epoch' in r and 'ended_at_epoch' in r])
            name = str(s.get('name') or '')
            seconds = float(s.get('seconds') or 0)
            if s.get('end') is None:
                signals.append({'id': 'N.open.%s' % sha(name.encode())[:8], 'type': 'open_node', 'stage': stage,
                                'evidence': '节点“%s”没有结束记录' % name})
            elif seconds >= LONG_NODE_SECONDS:
                signals.append({'id': 'N.long.%s' % sha((name + str(s.get('start'))).encode())[:8], 'type': 'long_node',
                                'stage': stage, 'evidence': '节点“%s”单次用了 %s' % (name, clock(seconds))})
            key = (stage, name)
            repeats.setdefault(key, [0, 0.0])
            repeats[key][0] += 1
            repeats[key][1] += seconds
        for (stage, name), (times, seconds) in sorted(repeats.items(), key=lambda x: (str(x[0][0]), x[0][1])):
            if times >= REPEAT_TIMES and name:
                signals.append({'id': 'N.repeat.%s' % sha(('%s|%s' % (stage, name)).encode())[:8], 'type': 'repeated_node',
                                'stage': stage, 'evidence': '节点“%s”在同一阶段执行了 %d 次，合计 %s' % (name, times, clock(seconds))})
    out['usage'] = usage(project, stage_windows(project), home)
    if out['usage']['available']:
        out['sources'].append('Codex 本机会话记录')
        active = [r for r in out['usage']['stages'] if r['total_tokens']]
        for r in active:
            if r['share'] >= DOMINANT_SHARE and len(active) > 1:
                signals.append({'id': 'U%d.%s.usage' % (r['stage'], r.get('entry', 0)), 'type': 'usage_dominant', 'stage': r['stage'],
                                'evidence': '第 %d 阶段用掉全程 %d%% 的模型用量（%s，%d 次调用）' % (
                                    r['stage'], round(r['share'] * 100), amount(r['total_tokens']), r['calls'])})
    ledger = project / 'docs/test/package-issues.jsonl'
    if ledger.is_file() and not ledger.is_symlink() and ledger.stat().st_size <= MAX_BYTES:
        out['sources'].append('docs/test/package-issues.jsonl')
        for line in ledger.read_text(encoding='utf-8', errors='replace').splitlines()[:200]:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if isinstance(row, dict):
                out['issues'].append({k: row[k] for k in ('id', 'title', 'status', 'stage', 'cause', 'fix') if k in row})
    outbox = project / 'docs/production-learning/outbox'
    if outbox.is_dir():
        out['experience_bundles'] = sorted(p.name for p in outbox.glob('*.json') if p.is_file())[:64]
    out['signal_ids'] = [s['id'] for s in signals]
    return out


# ---------------------------------------------------------------- check

def text_of(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return ' '.join(text_of(v) for v in value.values())
    if isinstance(value, list):
        return ' '.join(text_of(v) for v in value)
    return ''


def filled(value):
    return isinstance(value, str) and len(value.strip()) >= 2


def check(project, skill_root=None):
    project = Path(project).resolve()
    root = Path(skill_root).resolve() if skill_root else default_skill_root()
    home = project / OUT
    findings = []

    def bad(where, why):
        findings.append({'where': where, 'reason': why})

    fact_path, report_path = home / 'facts.json', home / 'lessons.json'
    fact_doc, report = read_json(fact_path), read_json(report_path)
    if not isinstance(fact_doc, dict) or fact_doc.get('schema') != SCHEMA_FACTS:
        bad('facts.json', '先运行 facts，复盘必须基于本作的真实记录')
        fact_doc = {'signal_ids': []}
    if not isinstance(report, dict) or report.get('schema') != SCHEMA_REPORT:
        bad('lessons.json', '缺少复盘文件或 schema 不是 ' + SCHEMA_REPORT)
        return {'passed': False, 'findings': findings, 'delivery_blocking': False}
    if fact_path.is_file() and report.get('facts_sha256') != sha(fact_path.read_bytes()):
        bad('facts_sha256', '复盘绑定的不是当前这份事实；事实更新后要重新复盘')
    reflection = report.get('reflection') if isinstance(report.get('reflection'), dict) else {}
    for key, label in (('went_well', '做得好的'), ('went_wrong', '做得不好的')):
        rows = reflection.get(key)
        if not isinstance(rows, list) or not rows or not all(filled(x) for x in rows):
            bad('reflection.' + key, '自我复盘要写出' + label + '，每条一句完整的话')
    if not filled(reflection.get('summary')):
        bad('reflection.summary', '缺少一句话总评')
    lessons = report.get('lessons') if isinstance(report.get('lessons'), list) else []
    if not lessons:
        bad('lessons', '至少一条经验；确实没有时写一条 decision=no_change 并说明为什么')
    answered, ids, patch_paths = set(), set(), {}
    for n, lesson in enumerate(lessons):
        where = 'lessons[%d]' % n
        if not isinstance(lesson, dict):
            bad(where, '不是对象')
            continue
        lid = lesson.get('id')
        where = 'lesson %s' % (lid or n)
        if not isinstance(lid, str) or not lid.strip() or lid in ids:
            bad(where, 'id 缺失或重复')
        ids.add(lid)
        for key, label in (('title', '标题'), ('what_happened', '发生了什么'), ('root_cause', '根因')):
            if not filled(lesson.get(key)):
                bad(where, '缺少' + label)
        if lesson.get('kind') not in KINDS:
            bad(where, 'kind 只能是 ' + '/'.join(KINDS))
        evidence = lesson.get('evidence')
        if not isinstance(evidence, list) or not evidence or not all(
                isinstance(e, dict) and filled(e.get('source')) and filled(e.get('detail')) for e in evidence):
            bad(where, '每条经验至少一条证据，写明出处和具体数字或原文；没有证据的只能算猜测')
        for sid in lesson.get('signal_ids') or []:
            if sid not in fact_doc.get('signal_ids', []):
                bad(where, '引用了不存在的信号 ' + str(sid))
            answered.add(sid)
        analysis = lesson.get('skill_analysis') if isinstance(lesson.get('skill_analysis'), dict) else {}
        read_files = analysis.get('read_files')
        if not isinstance(read_files, list) or not read_files:
            bad(where, 'skill_analysis.read_files 为空：必须先读 Skill 里相关的现有规则再下结论')
        else:
            for rel in read_files:
                target = inside(root, rel)
                if target is None or not target.is_file():
                    bad(where, '声称读过的 Skill 文件不存在：' + str(rel))
        for key, label in (('existing_rule', 'Skill 现在是怎么规定的'), ('why_not_prevented', '现有规定为什么没拦住'),
                           ('conflicts', '与现有规则是否冲突或重复')):
            if not filled(analysis.get(key)):
                bad(where, 'skill_analysis 缺少：' + label)
        patch = lesson.get('patch') if isinstance(lesson.get('patch'), dict) else {}
        decision = patch.get('decision')
        if decision not in DECISIONS:
            bad(where, 'patch.decision 只能是 ' + '/'.join(DECISIONS))
        if not filled(patch.get('reason')):
            bad(where, 'patch.reason 缺失：说明为什么改 Skill、只留在本作，或不改')
        if not isinstance(patch.get('adds_check'), bool):
            bad(where, 'patch.adds_check 必须明确写 true 或 false')
        prevention = lesson.get('prevention') if isinstance(lesson.get('prevention'), dict) else {}
        changes = patch.get('changes') if isinstance(patch.get('changes'), list) else []
        if decision == 'change_skill':
            if prevention.get('stage') not in (1, 2, 3, 4, 5) or not filled(prevention.get('action')):
                bad(where, '改 Skill 的经验必须写明下次在第几阶段、用什么制作动作预防')
            if patch.get('adds_check') and not filled(patch.get('adds_check_reason')):
                bad(where, '增加检查必须说明为什么制作阶段预防不了；只加一项检查不算吸收经验')
            if not changes:
                bad(where, 'decision=change_skill 但没有列出要改的文件')
        elif changes:
            bad(where, '不改 Skill 的经验不应带改动文件')
        for change in changes:
            rel = change.get('path') if isinstance(change, dict) else None
            target, staged = inside(root, rel), inside(home / 'patch' / '改动文件', rel)
            if target is None or staged is None:
                bad(where, '改动路径必须是 Skill 包内的相对路径：' + str(rel))
                continue
            if not filled(change.get('summary')):
                bad(where, rel + '：缺少一句话说明改了什么')
            before = change.get('before_sha256')
            if target.is_file():
                current = sha(target.read_bytes())
                if before != current:
                    bad(where, rel + '：before_sha256 不是当前已装 Skill 里这份文件，补丁底本过期')
            elif before is not None:
                bad(where, rel + '：Skill 里没有这个文件，新文件的 before_sha256 应为 null')
            if not staged.is_file() or staged.is_symlink():
                bad(where, rel + '：改好的文件没有放进 patch/改动文件/')
            elif target.is_file() and staged.read_bytes() == target.read_bytes():
                bad(where, rel + '：改好的文件与现有文件完全相同')
            elif rel in patch_paths and patch_paths[rel] != lid:
                pass  # several lessons may land in one file; the staged file is the merged result
            patch_paths.setdefault(rel, lid)
        words = text_of(lesson.get('prevention')) + ' ' + text_of(patch)
        for behaviour, needles in REVOKED_WORDS.items():
            if any(x in words for x in needles) and behaviour not in (lesson.get('mentions_revoked_only_to_avoid') or []):
                bad(where, '涉及已被永久撤销的做法：' + behaviour)
    unanswered = report.get('unanswered_signals') if isinstance(report.get('unanswered_signals'), list) else []
    for row in unanswered:
        if isinstance(row, dict) and filled(row.get('reason')):
            answered.add(row.get('signal_id'))
    for sid in fact_doc.get('signal_ids', []):
        if sid not in answered:
            bad('signal ' + sid, '这个信号没有被任何经验回答，也没有说明为什么不需要回答')
    staged_root = home / 'patch' / '改动文件'
    if staged_root.is_dir():
        for p in sorted(staged_root.rglob('*')):
            if p.is_file() and p.relative_to(staged_root).as_posix() not in patch_paths:
                bad('patch/改动文件/' + p.relative_to(staged_root).as_posix(), '补丁里有文件没有对应任何一条经验')
    return {'passed': not findings, 'findings': findings, 'delivery_blocking': False,
            'skill_base': skill_base(root), 'lessons': len(lessons), 'patch_files': sorted(patch_paths),
            'boundary': '只核对复盘是否完整、是否对照了当前 Skill；不代表补丁已审、已发版或已安装。'}


# ---------------------------------------------------------------- render

CSS = '''
:root{--bg:#f6f5f1;--card:#fff;--ink:#1d1d1b;--mute:#6b6a65;--line:#e2e0d8;--acc:#b4532a;--ok:#2f7a4f;--warn:#a8650b;--bar:#d9d5c8;--code:#f1efe8}
@media (prefers-color-scheme:dark){:root{--bg:#191917;--card:#232320;--ink:#ecebe6;--mute:#a09f98;--line:#383733;--acc:#e08a5f;--ok:#6cc08e;--warn:#e0a955;--bar:#45433d;--code:#2c2b27}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.7 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
main{max-width:880px;margin:0 auto;padding:32px 16px 64px}h1{font-size:28px;margin:0 0 4px}h2{font-size:20px;margin:40px 0 12px;padding-bottom:6px;border-bottom:1px solid var(--line)}
h3{font-size:17px;margin:0 0 8px}.sub{color:var(--mute);font-size:14px}.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin:12px 0}
.tag{display:inline-block;font-size:12px;padding:1px 8px;border-radius:99px;border:1px solid var(--line);color:var(--mute);margin-right:6px}
.tag.go{color:var(--ok);border-color:var(--ok)}.tag.warn{color:var(--warn);border-color:var(--warn)}
dl{display:grid;grid-template-columns:8.5em 1fr;gap:6px 12px;margin:10px 0 0}dt{color:var(--mute);font-size:14px}dd{margin:0}
@media (max-width:560px){dl{grid-template-columns:1fr}dt{margin-top:6px}}
table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--mute);font-weight:500}
.bar{height:8px;background:var(--bar);border-radius:4px;overflow:hidden;min-width:60px}.bar i{display:block;height:100%;background:var(--acc)}
pre{background:var(--code);padding:10px 12px;border-radius:8px;overflow:auto;font:12.5px/1.5 ui-monospace,Menlo,Consolas,monospace;margin:8px 0 0;max-height:360px}
.add{color:var(--ok)}.del{color:var(--acc)}ul{margin:6px 0;padding-left:1.3em}.banner{border-left:4px solid var(--warn);padding:10px 14px;background:var(--card);margin:16px 0}
code{background:var(--code);padding:0 4px;border-radius:4px;font-size:13px}.tw{overflow-x:auto}
'''


def esc(value):
    return html.escape(str(value if value is not None else ''))


def diff_html(before, after, rel):
    rows = list(difflib.unified_diff(before.splitlines(), after.splitlines(), 'Skill 现有/' + rel, '补丁/' + rel, lineterm='', n=1))
    if len(rows) > 160:
        rows = rows[:160] + ['… 其余 %d 行见补丁文件夹里的差异文件' % (len(rows) - 160)]
    out = []
    for line in rows:
        cls = 'add' if line.startswith('+') and not line.startswith('+++') else 'del' if line.startswith('-') and not line.startswith('---') else ''
        out.append('<span class="%s">%s</span>' % (cls, esc(line)) if cls else esc(line))
    return '<pre>' + '\n'.join(out) + '</pre>'


def render(project, skill_root=None):
    project = Path(project).resolve()
    root = Path(skill_root).resolve() if skill_root else default_skill_root()
    home = project / OUT
    verdict = check(project, root)
    report, fact_doc = read_json(home / 'lessons.json'), read_json(home / 'facts.json') or {}
    if not isinstance(report, dict):
        return dict(verdict, rendered=None)
    base = skill_base(root)
    patch_home, staged_root = home / 'patch', home / 'patch' / '改动文件'
    lessons = [x for x in report.get('lessons') or [] if isinstance(x, dict)]
    game = esc((report.get('game') or {}).get('label') or project.name)
    h = ['<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         '<title>复盘补丁报告</title><style>%s</style></head><body><main>' % CSS,
         '<h1>复盘补丁报告</h1><div class="sub">%s · 对照的 Skill：%s · 由制作本作的 AI 在交付后自动复盘生成</div>' % (game, esc(base['revision']))]
    if not verdict['passed']:
        h.append('<div class="banner"><b>这份复盘还没写完整，不能作为补丁依据。</b><ul>%s</ul></div>' % ''.join(
            '<li>%s：%s</li>' % (esc(f['where']), esc(f['reason'])) for f in verdict['findings'][:20]))
    change_n = sum(1 for x in lessons if (x.get('patch') or {}).get('decision') == 'change_skill')
    h.append('<div class="card"><b>结论：</b>%s<div class="sub" style="margin-top:6px">共 %d 条经验，其中 %d 条建议改 Skill，涉及 %d 个文件；%d 条会增加检查。在你批准之前，没有任何 Skill 文件被修改。</div></div>' % (
        esc((report.get('reflection') or {}).get('summary')), len(lessons), change_n, len(verdict.get('patch_files') or []),
        sum(1 for x in lessons if (x.get('patch') or {}).get('adds_check') is True)))
    stages = fact_doc.get('stages') or []
    if stages:
        h.append('<h2>一、这次制作用时</h2><div class="card tw"><table><tr><th>阶段</th><th>墙钟</th><th>实际工作</th><th>等待</th><th>没有记录</th><th>占比</th></tr>')
        for s in stages:
            h.append('<tr><td>%d %s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td><div class="bar"><i style="width:%d%%"></i></div>%d%%</td></tr>' % (
                s['stage'], esc(s.get('name')), clock(s['wall_seconds']), clock(s['work_seconds']), clock(s['wait_seconds']),
                clock(s['unrecorded_seconds']), round(s['share'] * 100), round(s['share'] * 100)))
        h.append('</table></div>')
    used = fact_doc.get('usage') if isinstance(fact_doc.get('usage'), dict) else {}
    if used.get('available'):
        h.append('<h2>各阶段消耗的额度</h2><div class="card tw"><table><tr><th>阶段</th><th>模型调用</th><th>总用量</th><th>其中非缓存</th><th>周额度</th><th>占比</th></tr>')
        for r in used.get('stages') or []:
            quota = ('+%s%%' % ('%g' % r['quota_percent_delta'])) if 'quota_percent_delta' in r else esc(r.get('quota_note') or '无读数')
            if r.get('other_sessions_overlapping'):
                quota += ' <span class="sub">（同时段另有 %d 个会话）</span>' % r['other_sessions_overlapping']
            h.append('<tr><td>%d %s</td><td>%d 次</td><td>%s</td><td>%s</td><td>%s</td><td><div class="bar"><i style="width:%d%%"></i></div>%d%%</td></tr>' % (
                r['stage'], esc(STAGE_NAMES.get(r['stage'], '')), r['calls'], amount(r['total_tokens']), amount(r['uncached_tokens']), quota,
                round(r['share'] * 100), round(r['share'] * 100)))
        extra = used.get('outside_stages') or {}
        if extra.get('total_tokens'):
            h.append('<tr><td>阶段之外</td><td>%d 次</td><td>%s</td><td>%s</td><td></td><td></td></tr>' % (
                extra['calls'], amount(extra['total_tokens']), amount(extra['uncached_tokens'])))
        h.append('</table><div class="sub" style="margin-top:8px">%s 共 %d 个会话。</div></div>' % (esc(used.get('boundary')), used.get('sessions') or 0))
    elif used.get('reason'):
        h.append('<div class="sub">额度：%s。</div>' % esc(used['reason']))
    reflection = report.get('reflection') or {}
    h.append('<h2>二、自我复盘</h2><div class="card"><h3>做得好的</h3><ul>%s</ul><h3 style="margin-top:14px">做得不好的</h3><ul>%s</ul></div>' % (
        ''.join('<li>%s</li>' % esc(x) for x in reflection.get('went_well') or []),
        ''.join('<li>%s</li>' % esc(x) for x in reflection.get('went_wrong') or [])))
    signals = fact_doc.get('signals') or []
    if signals:
        owner = {}
        for x in lessons:
            for sid in x.get('signal_ids') or []:
                owner.setdefault(sid, []).append(x.get('id'))
        skipped = {r.get('signal_id'): r.get('reason') for r in report.get('unanswered_signals') or [] if isinstance(r, dict)}
        h.append('<h2>三、记录里自动发现的异常</h2><div class="sub">工具从计时和问题记录里挑出来的，每一条都必须有回答。</div><div class="card tw"><table><tr><th>异常</th><th>回答</th></tr>')
        for s in signals:
            answer = '见经验 ' + '、'.join(esc(x) for x in owner[s['id']]) if s['id'] in owner else (
                '不处理：' + esc(skipped[s['id']]) if s['id'] in skipped else '<span class="del">未回答</span>')
            h.append('<tr><td>%s</td><td>%s</td></tr>' % (esc(s.get('evidence')), answer))
        h.append('</table></div>')
    h.append('<h2>四、经验，以及它下次放进 Skill 的哪里</h2>')
    label = {'change_skill': ('改 Skill', 'go'), 'project_only': ('只留在本作', ''), 'no_change': ('不改', '')}
    kind = {'process': '流程', 'tool': '工具', 'rule_gap': '规则缺口', 'project_only': '本作特有'}
    for x in lessons:
        patch, analysis, prevention = x.get('patch') or {}, x.get('skill_analysis') or {}, x.get('prevention') or {}
        text, cls = label.get(patch.get('decision'), ('未定', 'warn'))
        h.append('<div class="card"><h3>%s　%s</h3><span class="tag %s">%s</span><span class="tag">%s</span>%s<dl>' % (
            esc(x.get('id')), esc(x.get('title')), cls, text, esc(kind.get(x.get('kind'), x.get('kind'))),
            '<span class="tag warn">会增加检查</span>' if patch.get('adds_check') else '<span class="tag">不增加检查</span>'))
        h.append('<dt>发生了什么</dt><dd>%s</dd>' % esc(x.get('what_happened')))
        h.append('<dt>证据</dt><dd><ul>%s</ul></dd>' % ''.join('<li>%s <span class="sub">（%s）</span></li>' % (
            esc(e.get('detail')), esc(e.get('source'))) for e in x.get('evidence') or [] if isinstance(e, dict)))
        h.append('<dt>根因</dt><dd>%s</dd>' % esc(x.get('root_cause')))
        h.append('<dt>Skill 现在的规定</dt><dd>%s<div class="sub">读过：%s</div></dd>' % (
            esc(analysis.get('existing_rule')), '、'.join('<code>%s</code>' % esc(p) for p in analysis.get('read_files') or [])))
        h.append('<dt>为什么没拦住</dt><dd>%s</dd>' % esc(analysis.get('why_not_prevented')))
        h.append('<dt>和现有规则</dt><dd>%s</dd>' % esc(analysis.get('conflicts')))
        if prevention.get('action'):
            h.append('<dt>下次怎么预防</dt><dd>第 %s 阶段：%s</dd>' % (esc(prevention.get('stage')), esc(prevention.get('action'))))
        h.append('<dt>处理决定</dt><dd>%s%s</dd>' % (esc(patch.get('reason')), (
            '<div class="sub">增加检查的理由：%s</div>' % esc(patch.get('adds_check_reason'))) if patch.get('adds_check') else ''))
        for change in patch.get('changes') or []:
            rel = change.get('path') if isinstance(change, dict) else None
            target, staged = inside(root, rel), inside(staged_root, rel)
            if target is None or staged is None or not staged.is_file():
                continue
            before = target.read_text(encoding='utf-8', errors='replace') if target.is_file() else ''
            after = staged.read_text(encoding='utf-8', errors='replace')
            h.append('<dt>改这个文件</dt><dd><code>%s</code>%s<br>%s%s</dd>' % (
                esc(rel), '（新文件）' if not target.is_file() else '', esc(change.get('summary')), diff_html(before, after, rel)))
        h.append('</dl></div>')
    files = verdict.get('patch_files') or []
    h.append('<h2>五、待你批准</h2><div class="card">')
    if files and verdict['passed']:
        h.append('补丁已备好，放在本作的 <code>%s/patch/</code>：改好的 %d 个文件、底本校验、逐行差异，和一段可以直接发给英化 Skill 会话的话。<ul><li>同意：把那段话发给英化 Skill 会话，由它合入下一版并安装。</li><li>不同意某条：直接说编号，那一条不进补丁。</li></ul>在此之前，已装的 Skill 不会有任何变化；游戏交付也不受这份报告影响。' % (esc(OUT), len(files)))
    elif files:
        h.append('复盘还没通过完整性核对，补丁暂时不能交出去。')
    else:
        h.append('这次没有需要改 Skill 的经验，不产生补丁。')
    h.append('</div></main></body></html>')
    out = home / '复盘补丁报告.html'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('\n'.join(h), encoding='utf-8')
    result = dict(verdict, rendered=str(out))
    if files and verdict['passed']:
        lines, shas, diffs = [], [], []
        for rel in files:
            target, staged = inside(root, rel), inside(staged_root, rel)
            before = target.read_bytes() if target.is_file() else None
            after = staged.read_bytes()
            lines.append('%s\t%s' % ('新增' if before is None else '修改', rel))
            shas.append('%s  %s\n  底本 %s' % (sha(after), rel, sha(before) if before is not None else '（新文件）'))
            diffs.extend(difflib.unified_diff((before or b'').decode('utf-8', 'replace').splitlines(),
                                              after.decode('utf-8', 'replace').splitlines(), 'a/' + rel, 'b/' + rel, lineterm=''))
        (patch_home / '改动文件清单.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
        (patch_home / '改动文件与底本SHA256.txt').write_text('\n'.join(shas) + '\n', encoding='utf-8')
        (patch_home / '相对已装Skill的差异.patch').write_text('\n'.join(diffs) + '\n', encoding='utf-8')
        note = ['请合入这份由游戏会话交付后自动复盘得到的补丁。', '',
                '底本：已装英化 Skill，%s。每个文件的底本 SHA-256 见 改动文件与底本SHA256.txt，合入前请先核对。' % base['revision'],
                '先读同级目录的 复盘补丁报告.html：每条经验都写了证据、根因、对照过的现有规则、下次在哪个阶段预防。', '',
                '经验与改动：']
        for x in lessons:
            patch = x.get('patch') or {}
            if patch.get('decision') == 'change_skill':
                note.append('- %s %s → %s%s' % (x.get('id'), x.get('title'), '、'.join(c.get('path') for c in patch.get('changes') or []),
                                               '（会增加检查）' if patch.get('adds_check') else ''))
        note += ['', '这份补丁没有安装、没有占版本号、没有改 PROVENANCE 和更新记录、没有跑发版自检，这些请按发版流程做。',
                 '与其他待合补丁有冲突或重复时以你的合并判断为准；不采纳的条目请在版本登记里写明原因。']
        (patch_home / '发给英化skill_复盘补丁_复制这段话.txt').write_text('\n'.join(note) + '\n', encoding='utf-8')
        result['patch_folder'] = str(patch_home)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='cmd', required=True)
    for name in ('facts', 'usage', 'check', 'render'):
        p = sub.add_parser(name)
        p.add_argument('--project', required=True)
        if name in ('check', 'render'):
            p.add_argument('--skill-root', help='默认是本工具所在的已装 Skill 根目录')
        else:
            p.add_argument('--codex-home', help='默认 CODEX_HOME 或用户目录下的 .codex')
        if name == 'usage':
            p.add_argument('--no-write', action='store_true', help='只打印，不写 docs/timing/usage-summary.json')
    a = parser.parse_args(argv)
    if a.cmd == 'facts':
        doc = facts(a.project, a.codex_home)
        path = write_json(Path(a.project).resolve() / OUT / 'facts.json', doc)
        result = {'facts': str(path), 'facts_sha256': sha(path.read_bytes()), 'signals': doc['signals'], 'delivery_blocking': False}
    elif a.cmd == 'usage':
        result = dict(usage(a.project, stage_windows(a.project), a.codex_home), schema='stage-usage-summary.v1', delivery_blocking=False)
        if not a.no_write and result['available']:
            result['written'] = str(write_json(Path(a.project).resolve() / 'docs/timing/usage-summary.json', result))
        for r in result.get('stages') or []:
            print('第 %d 阶段：%d 次调用，用量 %s（非缓存 %s），周额度 %s，占 %d%%' % (
                r['stage'], r['calls'], amount(r['total_tokens']), amount(r['uncached_tokens']),
                ('+%g%%' % r['quota_percent_delta']) if 'quota_percent_delta' in r else '无读数', round(r['share'] * 100)), file=sys.stderr)
    elif a.cmd == 'check':
        result = check(a.project, a.skill_root)
    else:
        result = render(a.project, a.skill_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    # Exit 2 only says the reflection needs more work; it never gates a game delivery.
    return 0 if result.get('passed', True) else 2


if __name__ == '__main__':
    sys.exit(main())
