#!/usr/bin/env python3
"""Art-check receipt (v7.8, 总表 U7（补）; Saul 10-30 agreed, his 10-24 decision stands).

Art is checked once, at the art stage, by art_check.py. Packaging never re-runs it (Saul 10-24: a second run can differ);
the package writers and the user-trial preview only CHECK this receipt, so "art changed after the art check and nobody
looked" (丛林荡藤 v1-v6, 企鹅雪道美术 v1-v6, Holly v1-v3) cannot reach a ZIP or a trial link.

  <project>/.tiktok-kit/art-receipt.json
    kind art-receipt, schema 1
    status   pass            art_check's full analysis ran and found nothing to fix
             fail            the analysis ran and found something (the writers refuse it like a missing receipt)
             not_covered_3x  Cocos 3.x project: ui_dump cannot read 3.x pages yet, so the art check could not run.
                             Never a pass: the writers let it through and print "3.x 未覆盖" in their result/table.
    art_check {report, report_sha256, status, checked, failed, time, board}   which art-check.json it stands for
    tools    sha256 of art_check.py and art_receipt.py (recorded only; a Skill update does not force a re-run)
    images   {project-relative path: sha256} of every image under assets/: .png .jpg .jpeg .webp (and .bmp .tga .psd
             .tif .tiff .hdr), atlas .plist files, 3D model files .fbx .gltf .glb (their embedded textures are covered by
             the file fingerprint); library/, temp/, build/, .tiktok-kit/ ... are skipped
    images_sha256, images_count, created, engine, carried (see below)
  Why .tiktok-kit/: the writers already read <project>/.tiktok-kit/ (finalize-source.json, policy.json); the folder is
  outside the source digest of tiktok_finalize (K5) and outside every art scan, so writing the receipt changes nothing
  the receipt or K5 measures. art_check's own report stays in its timestamped --out folder outside the project.

Who writes it
  art_check.py (full mode only, not --loading-only / --ui-contract): after its analysis -> pass or fail. When its
  inputs are missing (blocked_inputs, no verdict) an existing receipt is left alone on Cocos 2.4; on Cocos 3.x the
  receipt becomes not_covered_3x for the current images.
  tiktok_finalize.py source: its `images` step converts WebP to PNG/JPG and shrinks oversized textures, which changes
  image bytes the art check saw. It checks the receipt BEFORE any step and, only when every image still matched,
  carries the receipt to the bytes it wrote itself (`carried` lists what it changed). A receipt that no longer matched
  before the source phase is left as it is, so the writer still refuses.

Who checks it (check())
  make_tiktok_zip.finalize_for_writer (both writers: make_tiktok_zip.py and build_checked_zip.py) and
  serve_preview.py --keep. A NEW remake game (board remake, policy new) with no receipt, a receipt that is not a pass,
  or images that differ from the receipt is refused: "美术改过（或没跑美术检查），重跑 art_check" plus the changed
  images. Legacy games (policy legacy) and English games (board localize) get the same text as a warning. A project
  without any image under assets/ has no art to check (state no_images, passes; real games never hit this).
"""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
RECEIPT = Path('.tiktok-kit') / 'art-receipt.json'
SOURCE_RECORD = Path('.tiktok-kit') / 'finalize-source.json'
MARKER = Path('.tiktok-kit') / 'policy.json'
SCHEMA = 1
IMAGE_SUFFIXES = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tga', '.psd', '.tif', '.tiff', '.hdr',
                  '.plist', '.fbx', '.gltf', '.glb')
SKIP_DIRS = {'library', 'temp', 'local', 'build', 'node_modules', '.git', 'profiles', '.tiktok-kit', '__macosx'}
GATE = 'ART_receipt'
GATE_3X = 'ART_receipt_3x_not_covered'
GATE_BASE_AUDIO = 'ART_base_audio'
RERUN = '美术改过（或没跑美术检查），重跑 art_check'
STATUSES = ('pass', 'fail', 'not_covered_3x')


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def receipt_path(project):
    return Path(project) / RECEIPT


def image_fingerprints(project):
    """{project-relative posix path: sha256} of every image / atlas / 3D model file under <project>/assets/."""
    project = Path(project)
    root = project / 'assets'
    out = {}
    if not root.is_dir():
        return out
    for p in sorted(root.rglob('*')):
        if not p.is_file() or p.is_symlink() or not p.name.lower().endswith(IMAGE_SUFFIXES):
            continue
        rel = p.relative_to(project)
        if SKIP_DIRS & {x.lower() for x in rel.parts[:-1]} or p.name.startswith('._'):
            continue
        out[rel.as_posix()] = _sha(p.read_bytes())
    return out


def images_digest(images):
    return _sha(json.dumps(images, sort_keys=True, separators=(',', ':')).encode('utf-8'))


def engine(project):
    """2 | 3 | None, from project.json / package.json (as tiktok_finalize does); settings/v2 means 3.x."""
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    from tiktok_finalize_steps import policy as P
    found = P.engine_of_project(project)
    if found is None and (Path(project) / 'settings' / 'v2').is_dir():
        return 3
    return found


def _tool_hashes():
    out = {}
    for name in ('art_check.py', 'art_receipt.py'):
        f = HERE / name
        out[name] = _sha(f.read_bytes()) if f.is_file() else None
    return out


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.art-receipt-', dir=path.parent)
    os.close(fd)
    try:
        Path(tmp).write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def write(project, status, report=None, report_path=None, note=None):
    """Write the receipt for the CURRENT images of `project`. report = art_check's art-check.json content."""
    if status not in STATUSES:
        raise ValueError('art receipt status must be one of %s' % (STATUSES,))
    project = Path(project).resolve()
    images = image_fingerprints(project)
    report = report or {}
    rpath = Path(report_path).resolve() if report_path else None
    receipt = {
        'kind': 'art-receipt', 'schema': SCHEMA, 'status': status, 'passed': status == 'pass',
        'project': str(project), 'engine': engine(project),
        'art_check': {'report': str(rpath) if rpath else None,
                      'report_sha256': _sha(rpath.read_bytes()) if rpath and rpath.is_file() else None,
                      'status': report.get('status'), 'checked': report.get('checked'), 'failed': report.get('failed'),
                      'time': report.get('time'), 'board': report.get('board')},
        'tools': _tool_hashes(),
        'created': dt.datetime.now().astimezone().isoformat(timespec='seconds'),
        'images_count': len(images), 'images_sha256': images_digest(images),
        'art_check_images_sha256': images_digest(images), 'images': images, 'carried': []}
    if isinstance(report.get('base_generated'), dict):
        receipt['base_generated'] = report['base_generated']      # v7.8 H8 / H10 summary (art_records.summary)
    if note:
        receipt['note'] = note
    _write_json(receipt_path(project), receipt)
    return receipt


def after_art_check(project, report, report_path):
    """art_check.py full mode, after the analysis ran: pass -> status pass, anything else -> fail."""
    return write(project, 'pass' if report.get('passed') is True else 'fail', report, report_path)


def not_covered_3x(project, report, report_path):
    """art_check.py on a Cocos 3.x project whose pages could not be captured (ui_dump has no 3.x support yet)."""
    return write(project, 'not_covered_3x', report, report_path,
                 note='3.x 未覆盖：ui_dump 还读不了 Cocos 3.x 页面，美术检查没有跑；只记录图片指纹，不是通过')


def read(project):
    """-> (receipt dict or None, error text or None)."""
    path = receipt_path(project)
    if not path.is_file():
        return None, None
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        return None, 'unreadable: %s' % error
    if not isinstance(data, dict) or data.get('kind') != 'art-receipt' or not isinstance(data.get('images'), dict):
        return None, 'not an art receipt (kind/images missing)'
    return data, None


def _json(path):
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def strictness(project, board=None, policy=None):
    """(strict, board, policy): strict = a new remake game (refuse); else warn only.
    board: given > source record > policy marker > docs/board.txt > remake (art_check's default).
    policy: given > source record (K5 keeps it current at the writers) > tiktok_finalize policy decision."""
    project = Path(project)
    record = _json(project / SOURCE_RECORD)
    marker = _json(project / MARKER)
    if not board:
        board = record.get('board') or marker.get('board')
    if not board:
        f = project / 'docs' / 'board.txt'
        text = f.read_text(encoding='utf-8').strip().lower() if f.is_file() else ''
        board = text if text in ('remake', 'localize') else 'remake'
    if policy not in ('new', 'legacy'):
        policy = record.get('policy')
    if policy not in ('new', 'legacy'):
        if str(HERE) not in sys.path:
            sys.path.insert(0, str(HERE))
        from tiktok_finalize_steps import policy as P
        try:
            policy = P.decide(project=project)['policy']
        except Exception:  # noqa: BLE001 - unreadable legacy list: a game not on it is new (Saul Q1)
            policy = 'new'
    return board == 'remake' and policy == 'new', board, policy


def diff(old, new):
    changed = sorted(k for k in new if k in old and old[k] != new[k])
    added = sorted(k for k in new if k not in old)
    removed = sorted(k for k in old if k not in new)
    return changed, added, removed


def _list(items, n=8):
    return '、'.join(items[:n]) + ('……共 %d 张' % len(items) if len(items) > n else '')


def check(project, board=None, policy=None):
    """Read-only. -> {'state', 'level' ok|warn|block, 'gate', 'message', 'changed', 'added', 'removed', 'status',
    'board', 'policy', 'strict', 'receipt', 'images_count', 'engine', 'base_audio'}.
    state: no_images | missing | unreadable | not_pass | changed | match_pass | match_3x.
    v7.8 H8: sounds are not in the image receipt, so the sounds are compared with the recorded base here as well
    (art_records.base_audio_now, a hash compare, not an art check): a sound still byte-identical to the base and not in
    docs/art/base-keep.json refuses a new remake game (gate ART_base_audio) and warns otherwise."""
    out = _check_images(project, board, policy)
    try:
        if str(HERE) not in sys.path:
            sys.path.insert(0, str(HERE))
        import art_records
        same = art_records.base_audio_now(Path(project).resolve(), out['board'])
    except Exception as error:  # noqa: BLE001 - the art check reported the base already; never crash the writer
        same = []
        out['base_audio_error'] = repr(error)
    out['base_audio'] = same
    if same:
        level = 'block' if out['strict'] else 'warn'
        text = ('和底子逐字节相同的声音 %d 个没换（H8）：%s；换成音频库里的，确实要留的写进 docs/art/base-keep.json 并写 why'
                % (len(same), _list(same)))
        if out['level'] == 'ok':
            out.update(level=level, gate=GATE_BASE_AUDIO, message=text)
        else:
            out['message'] += '；' + text
            if level == 'block' and out['level'] != 'block':
                out.update(level='block', gate=GATE_BASE_AUDIO)
    return out


def _check_images(project, board=None, policy=None):
    project = Path(project).resolve()
    strict, board, policy = strictness(project, board, policy)
    current = image_fingerprints(project)
    receipt, error = read(project)
    out = {'project': str(project), 'receipt': str(receipt_path(project)), 'board': board, 'policy': policy,
           'strict': strict, 'images_count': len(current), 'changed': [], 'added': [], 'removed': [],
           'status': (receipt or {}).get('status'), 'gate': GATE}
    try:
        out['engine'] = engine(project)
    except Exception:  # noqa: BLE001
        out['engine'] = None
    fix = '运行 `art_check.py --project %s`，全部通过后自动写回执' % project
    if not current:
        out.update(state='no_images', level='ok', message='工程 assets/ 下没有图片，没有美术要核对')
        return out
    if receipt is None:
        out.update(state='unreadable' if error else 'missing')
        why = '美术检查回执 %s %s' % (out['receipt'], '读不了（%s）' % error if error else '不存在')
    else:
        out['changed'], out['added'], out['removed'] = diff(receipt['images'], current)
        moved = out['changed'] or out['added'] or out['removed']
        status = receipt.get('status')
        if moved:
            parts = []
            for label, key in (('改了', 'changed'), ('新增', 'added'), ('删了', 'removed')):
                if out[key]:
                    parts.append('%s %d 张：%s' % (label, len(out[key]), _list(out[key])))
            out['state'] = 'changed'
            why = '回执（%s，%s）之后图片变了，%s' % (status, receipt.get('created'), '；'.join(parts))
        elif status == 'pass':
            out.update(state='match_pass', level='ok',
                       message='美术回执对得上：art_check 通过（%s），%d 张图未改' % (receipt.get('created'), len(current)))
            return out
        elif status == 'not_covered_3x' and out['engine'] == 3:
            out.update(state='match_3x', level='warn', gate=GATE_3X,
                       message='3.x 未覆盖：ui_dump 还读不了 Cocos 3.x 页面，美术检查没有跑（不是通过）；回执里 %d 张图未改'
                       % len(current))
            return out
        else:
            out['state'] = 'not_pass'
            why = '回执不是通过（status %s%s）' % (status, '，art_check 失败 %s 项' % (receipt.get('art_check') or {}).get(
                'failed') if status == 'fail' else '')
            bg = receipt.get('base_generated') or {}
            extra = []
            if bg.get('base_ok') is False:
                extra.append('底子原图原声 %s 个没换没登记' % bg.get('base_unlisted') if bg.get('base_state') == 'checked'
                             else '没有底子记录 docs/art/base-assets.json')
            if bg.get('generated_ok') is False:
                extra.append('不是生成的图 %s 张' % bg.get('not_generated'))
            if extra:
                why += '，其中 ' + '、'.join(extra)
    out['level'] = 'block' if strict else 'warn'
    scope = '重塑新游戏，不出包、不起试玩' if strict else ('旧游戏只警告' if policy == 'legacy' else '英化游戏只警告')
    out['message'] = '%s（%s）：%s；%s' % (RERUN, scope, why, fix)
    return out


def finding(result):
    """The check() result as a tiktok_finalize finding (id, level, message, evidence) or None when ok."""
    if result['level'] == 'ok':
        return None
    evidence = {k: result.get(k) for k in ('state', 'status', 'board', 'policy', 'receipt')}
    evidence.update({k: result[k][:50] for k in ('changed', 'added', 'removed')})
    evidence['base_audio'] = list(result.get('base_audio') or [])[:50]
    return {'id': result['gate'], 'level': 'block' if result['level'] == 'block' else 'warn',
            'message': result['message'], 'evidence': evidence}


ROW = {'no_images': '没有图片，不用核对', 'match_pass': '对得上（art_check 通过）', 'match_3x': '3.x 未覆盖（不是通过）',
       'missing': '没有回执', 'unreadable': '回执读不了', 'not_pass': '回执不是通过', 'changed': '图片改过'}


def table_row(result):
    """One row for tiktok_finalize's delivery table (step / result / changed / warnings)."""
    text = ROW.get(result['state'], result['state'])
    if result.get('base_audio'):
        text += '；底子原声 %d 个没换' % len(result['base_audio'])
    if result['level'] == 'warn' and result['state'] != 'match_3x':
        text += '（%s，警告）' % ('旧游戏' if result['policy'] == 'legacy' else '英化')
    elif result['level'] == 'block':
        text = '拒绝：' + text
    return {'step': 'art_receipt', 'result': text, 'changed': 0, 'warnings': 1 if result['level'] == 'warn' else 0}


def summary(result):
    """Short form for the writer record / report (no full image lists)."""
    out = {k: result.get(k) for k in ('state', 'level', 'status', 'board', 'policy', 'engine', 'images_count', 'receipt')}
    out.update({k: result[k][:20] for k in ('changed', 'added', 'removed')})
    out['base_audio'] = list(result.get('base_audio') or [])[:20]
    out['message'] = result.get('message')
    return out


def carry(project, by, before=None):
    """tiktok_finalize source: the receipt matched every image BEFORE the steps (`before` = check() then); move it to
    the bytes the steps wrote. Does nothing (returns None) unless that earlier check matched."""
    if not before or before.get('state') not in ('match_pass', 'match_3x', 'not_pass') or before.get('changed') \
            or before.get('added') or before.get('removed'):
        return None
    receipt, _ = read(project)
    if receipt is None:
        return None
    current = image_fingerprints(project)
    changed, added, removed = diff(receipt['images'], current)
    if not (changed or added or removed):
        return receipt
    receipt['carried'] = list(receipt.get('carried') or []) + [{
        'by': by, 'time': dt.datetime.now().astimezone().isoformat(timespec='seconds'),
        'changed': changed[:200], 'added': added[:200], 'removed': removed[:200],
        'why': 'the receipt matched every image before this run; only this run changed these files'}]
    receipt['images'] = current
    receipt['images_count'] = len(current)
    receipt['images_sha256'] = images_digest(current)
    _write_json(receipt_path(project), receipt)
    return receipt


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description='Read-only: does <project>/.tiktok-kit/art-receipt.json match the images?')
    ap.add_argument('--project', required=True, type=Path)
    ap.add_argument('--board', choices=('remake', 'localize'))
    a = ap.parse_args(argv)
    result = check(a.project, a.board)
    print(json.dumps(summary(result), ensure_ascii=False, indent=1))
    return 1 if result['level'] == 'block' else 0


if __name__ == '__main__':
    sys.exit(main())
