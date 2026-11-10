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


def write(project, status, report, report_path=None, board=None, scoped=None):
    """Called by art_check.py after a full-mode run (scoped = maintenance / English visual scope names, if any)."""
    if status not in ('pass', 'fail', 'not_covered_3x'):
        raise ValueError('art-check record status must be pass, fail or not_covered_3x')
    project = Path(project).resolve()
    old = read(project) or {}
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
        rows = '、'.join(str(r) for r in (last.get('blocking_rows') or [])[:8]) or '见报告'
        return {'level': 'block', 'message': '最近一次 art_check 还有需处理项：%s（报告 %s）。修好后只复查这些行。'
                % (rows, last.get('report'))}
    if data.get('first_full_pass') or legacy:
        return {'level': 'ok', 'message': '美术技术检查：已有完整通过记录（%s）；最近一次 %s。'
                % ((data.get('first_full_pass') or {}).get('time', '旧回执'), last.get('status'))}
    if last.get('status') == 'not_covered_3x':
        return {'level': 'warn', 'message': 'Cocos 3.x：art_check 还读不了 3.x 页面，技术美术检查未覆盖（不是通过）。'}
    if earlier_trial:
        return {'level': 'ok', 'message': '美术技术检查：最近一次局部 art_check 通过；首轮已在旧版 Skill 交付过试玩。'}
    return {'level': 'block', 'message': '只有局部范围的 art_check 记录，首轮还缺一次完整运行。' + FIX}
