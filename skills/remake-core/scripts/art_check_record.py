#!/usr/bin/env python3
"""Lightweight art-check record (11.17.14). Read/write only; never runs art_check itself.

Why: 11.17.13 removed the aggregate art receipt, because it bound every image fingerprint and forced a full art re-run
after each small edit. Without anything in its place, nothing showed that the technical art rows (dark bold text,
clarity, plain backgrounds, text fit, page content ...) had been run even once before the first English trial link.

This record keeps only "which art_check ran last and what it found" plus "when a full run first passed". It binds NO
image, text or layout fingerprints, so later edits never invalidate it and never force a re-run. The AI re-runs only the
affected rows when it changes art; if that later run reports blocking rows, the record says so until they are fixed.

  <project>/.tiktok-kit/art-check-record.json
    kind art-check-record, schema 1, board, engine
    last              {status pass|fail|not_covered_3x, failed, blocking_rows, report, report_sha256, time, scoped}
    first_full_pass   {time, report} of the first full (unscoped) passing run, kept forever; null until then

.tiktok-kit/ is outside the tiktok_finalize source digest and every art scan, so writing it changes nothing measured.

check(project) -> {'level': 'ok'|'warn'|'block', 'message': str}
  English formal trial (cocos-game-to-english/scripts/serve_preview.py) calls it; drafts and returned-art previews do not.
  An old passing art-receipt.json (before 11.17.13) also counts as a first full pass; its fingerprints are not compared.
"""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import tempfile

RECORD = Path('.tiktok-kit/art-check-record.json')
LEGACY_RECEIPT = Path('.tiktok-kit/art-receipt.json')
SCHEMA = 1


def record_path(project):
    return Path(project) / RECORD


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _engine(project):
    try:
        from art_receipt import engine
        return engine(project)
    except Exception:  # noqa: BLE001 - engine is informative only
        return None


def read(project):
    path = record_path(project)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get('kind') == 'art-check-record' else None


def write(project, status, report, report_path=None, board=None, scoped=None, previous_sha=None):
    """Called by art_check.py after a full-mode run (scoped = maintenance / English visual scope names, if any)."""
    from preparation_cache import project_lock
    with project_lock(project):
        return _write(project, status, report, report_path, board, scoped, previous_sha)


def _write(project, status, report, report_path, board, scoped, previous_sha):
    if status not in ('pass', 'fail', 'not_covered_3x'):
        raise ValueError('art-check record status must be pass, fail or not_covered_3x')
    project = Path(project).resolve()
    old = read(project) or {}
    if previous_sha is not None and (old.get('last') or {}).get('report_sha256') != previous_sha:
        raise ValueError('另一轮美术结果已登记。读回当前结果，再决定还缺哪些项。')
    report = report or {}
    rpath = Path(report_path).resolve() if report_path else None
    now = dt.datetime.now().astimezone().isoformat(timespec='seconds')
    blocking = [r.get('check') for r in report.get('rows') or [] if isinstance(r, dict) and r.get('status') == '需处理']
    last = {'status': status, 'failed': report.get('failed'), 'blocking_rows': blocking[:40],
            'report': str(rpath) if rpath else None,
            'report_sha256': _sha(rpath) if rpath and rpath.is_file() else None,
            'time': now, 'scoped': list(scoped or [])}
    first = old.get('first_full_pass')
    if first is None and status == 'pass' and not scoped:
        first = {'time': now, 'report': last['report']}
    data = {'kind': 'art-check-record', 'schema': SCHEMA, 'board': board or old.get('board'),
            'engine': _engine(project), 'last': last, 'first_full_pass': first}
    path = record_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.art-check-record-', suffix='.json', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)
    return data


def _legacy_pass(project):
    path = Path(project) / LEGACY_RECEIPT
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return False
    return isinstance(data, dict) and data.get('status') == 'pass'


FIX = ('运行 python3 <skills>/remake-core/scripts/art_check.py --project <工程> --board localize --dumps <本轮采集目录> '
       '--build <Web 导出>（只在首轮必须跑一次完整的；之后改动只复查受影响的行，不重跑全套）')


def check(project, earlier_trial=False):
    """Read-only gate for the first formal English trial. Never compares image fingerprints.

    earlier_trial: a passed non-draft formal trial is already logged (or --reopen). Projects that passed their first
    round under an older Skill then only get a warning when no record exists, so nobody is forced into a full re-run.
    """
    data = read(project)
    legacy = _legacy_pass(project)
    if data is None:
        if legacy:
            return {'level': 'ok', 'message': '美术技术检查：沿用 11.17.13 前的通过回执（不再比对图片指纹）。'}
        if earlier_trial:
            return {'level': 'warn', 'message': '没有 art_check 记录，但这款已有通过的正式试玩；不补跑全套，'
                    '之后改美术时只跑受影响的行。'}
        return {'level': 'block', 'message': '首轮英文试玩前还没跑过 art_check 技术检查。' + FIX}
    last = data.get('last') or {}
    if last.get('status') == 'fail':
        rows = '、'.join(str(r) for r in (last.get('blocking_rows') or [])) or '见报告'
        if last.get('scoped'):
            next_step = '核实问题后按原局部检查范围补验。'
        else:
            try:
                trial_report(project)
            except (OSError, ValueError, KeyError) as error:
                next_step = (f'先核原报告和采集缺口（{error}）。恢复能核准的证据，再补缺项和受影响项。'
                             '原报告移位时可用 art_check.py --plan-trial --prior-report 定位。')
            else:
                next_step = '用 art_check.py --plan-trial 定位原失败组，修复后用 --resume-trial 补验。'
        return {'level': 'block', 'message': f'继续第 3 阶段美术修复。{rows}（原报告 {last.get("report")}）。'
                f'{next_step}通过后重新启动正式试玩。'}
    if data.get('first_full_pass') or legacy:
        return {'level': 'ok', 'message': '美术技术检查：已有完整通过记录（%s）；最近一次 %s。'
                % ((data.get('first_full_pass') or {}).get('time', '旧回执'), last.get('status'))}
    if last.get('status') == 'not_covered_3x':
        return {'level': 'warn', 'message': 'Cocos 3.x：art_check 还读不了 3.x 页面，技术美术检查未覆盖（不是通过）。'}
    if earlier_trial:
        return {'level': 'ok', 'message': '美术技术检查：最近一次局部 art_check 通过；首轮已在旧版 Skill 交付过试玩。'}
    return {'level': 'block', 'message': '只有局部范围的 art_check 记录，首轮还缺一次完整运行。' + FIX}


# A group is one existing checker, or a set that shares the same raw result.
# Keep the identifiers stable across report wording changes.
TRIAL_GROUPS = {
    'assets': ('docs/art/base-assets.json', 'docs/art/generated.json', 'production-assets.json'),
    'slots': ('visual-slots-result.json',),
    'coverage': ('page-coverage.json',),
    'text_fit': ('text-fit.json',),
    'values': ('value-presentation.json',),
    'atlas': ('atlas_slices', 'atlas_slices/report.json', 'sprite_sources.json'),
    'page': ('page_richness.json', 'clarity.json', 'clarity-group.json'),
    'reward': ('claim_double.json',),
    'background': ('screens.json',),
    'layout': ('ui_coverage.json', 'logs/extract_ui_layout.log'),
    'copy': ('copy.json',),
    'fonts': ('bitmap_letter_fonts.json',),
    'dev_text': ('dev_text.json',),
    'design': ('top_bar.json', 'level_plan.json'),
}


def trial_group(row):
    log = row.get('log')
    for group, logs in TRIAL_GROUPS.items():
        if log in logs:
            return group
    title = row.get('check', '')
    if title in ('读到的页面', '采集材料') or log == 'input-inventory.json':
        return 'inputs'
    if title.startswith(('底子原图原声不留', '新做的图都有生成记录')):
        return 'assets'
    if title in ('顶部资源栏', '关卡地图') or title.startswith('礼盒10帧动画'):
        return 'design'
    if title.startswith('布局（'):
        return 'layout'
    if title.startswith('大块深色与纯色底'):
        return 'background'
    raise ValueError(f'原报告有未识别的技术检查行 {title!r}。先核准对应工具与证据。')


def trial_report(project, prior_report=None):
    data = read(project) or {}
    last = data.get('last') or {}
    name, expected = last.get('report'), last.get('report_sha256')
    if data.get('board') != 'localize' or last.get('scoped') or not name or not expected:
        raise ValueError('先恢复首轮英化技术检查的原始报告及运行记录。')
    path = Path(prior_report).expanduser().resolve() if prior_report else Path(name)
    if not path.is_absolute():
        path = Path(project) / path
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('技术检查原报告已变化。恢复与运行记录对应的原文件。')
    report = json.loads(raw)
    if not isinstance(report, dict):
        raise ValueError('美术原报告格式无效。先恢复对应的原始报告。')
    rows, capture = report.get('rows'), report.get('capture_round')
    if (report.get('tool') != 'art_check' or report.get('board') != 'localize'
            or report.get('status') not in ('pass', 'fail') or report['status'] != last.get('status')
            or not isinstance(rows, list) or len(rows) != report.get('checked')
            or not all(isinstance(row, dict) and isinstance(row.get('check'), str) for row in rows)
            or not isinstance(capture, dict) or not capture.get('ready')):
        raise ValueError('需要有覆盖核准的首轮技术检查原报告。先定位缺失输入。')
    failed = [r['check'] for r in rows if r.get('status') == '需处理']
    if report.get('failed') != len(failed) or last.get('failed') != len(failed):
        raise ValueError('原报告的失败数与记录不一致。')
    required = (TRIAL_GROUPS.keys() - {'slots'}) | {'inputs'}
    if not required <= {trial_group(row) for row in rows}:
        raise ValueError('原报告没有覆盖所有必需检查组。先恢复缺项证据。')
    return report, expected, path


def trial_recheck_plan(project, affected=(), prior_report=None):
    report, digest, path = trial_report(project, prior_report)
    pending = [row for row in report['rows'] if row['status'] == '需处理']
    groups = {trial_group(row) for row in pending} | set(affected)
    return report, {'from_report': str(path), 'from_report_sha256': digest,
                    'rechecked_groups': sorted(groups), 'pending_before': [r['check'] for r in pending]}


def merge_trial_rows(previous, rows, recheck):
    fresh_titles = {row['check'] for row in rows}
    selected = set(recheck['rechecked_groups']) | {'inputs'}
    reused = []
    for row in previous['rows']:
        group = trial_group(row)
        if group not in selected:
            reused.append(row['check'])
        elif row['check'] in fresh_titles or row['status'] != '需处理':
            continue
        rows.append(dict(row, origin_report=row.get('origin_report') or recheck['from_report']))
    recheck['reused_rows'] = reused
