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
  images. Legacy remake games get a warning; English games now block and require current value-presentation runtime evidence (score-reward-1). A project
  without any image under assets/ has no art to check (state no_images, passes; real games never hit this).
"""
import datetime as dt
import hashlib
import json
import os
import re as _re
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
# R4Q3 (补查3 第 3 组): Saul's 「保留原画风」 record, read by the receipt (original_style.py owns the format)
KEEP_RECORD = Path('docs') / 'art' / 'keep_original_style.json'
GATE_KEEP = 'ART_receipt_kept_original_style'
DARK_AREA_ROW = '大块深色与纯色底（画风禁止项，不设亮度下限）'   # = art_check.DARK_AREA_TITLE


def _keep_record(project):
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import original_style
    return original_style.keep_record(project)


def _kept_by_record(project, receipt):
    """R4Q3: True when a failed English receipt failed ONLY on the dark-area row, art_check could not tell original
    pictures from new ones, and docs/art/keep_original_style.json records Saul's choice to keep the original art."""
    style = receipt.get('original_style') or {}
    return (receipt.get('blocking_rows') == [DARK_AREA_ROW] and style.get('applies') == 'not_applicable'
            and style.get('state') in ('no_original', 'unmeasured') and bool(_keep_record(project)))


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


# 生成时预防 R4M2 (补查第 12 组): the receipt also stands for the TEXT, FONTS and LAYOUT on screen, so changing a label,
# a font file or a node's position / size after the art check makes the receipt stale like a changed image.
#   fonts   .ttf .otf .ttc .woff .woff2 .fnt: file bytes
#   layout  .fire .scene .prefab: only what decides the picture (node name / position / size / anchor / scale / rotation
#           / active / opacity / colour / parent, and every field of Label, RichText, Sprite, Widget, Layout,
#           UITransform, UIOpacity, outline / shadow, Mask, ScrollView / PageView parts); script components and
#           gameplay values stored in a prefab are NOT in it, so tuning numbers does not force a new art check
#   text    text tables (assets/**/(i18n|lang|locale|localization|strings|texts)/*.json or file names like lang_*.json)
#           and string literals a script writes into a label (`.string = '...'`, `.text = '...'`)
# Receipts written before R4M2 have no `display` field: their images are still compared, the display part is reported
# as `display_unrecorded` (no block), and the next art_check writes it. tiktok_finalize source carries display
# changes its own steps made, like images.
DISPLAY_SCHEMA = 1
FONT_SUFFIXES = ('.ttf', '.otf', '.ttc', '.woff', '.woff2', '.fnt')
LAYOUT_SUFFIXES = ('.fire', '.scene', '.prefab')
TEXT_TABLE_DIRS = {'i18n', 'lang', 'langs', 'language', 'languages', 'locale', 'locales', 'localization', 'l10n',
                   'strings', 'text', 'texts'}
TEXT_TABLE_PREFIX = ('lang', 'i18n', 'locale', 'strings', 'text_', 'texts')
KIT_SCRIPT_DIRS = {'tiktok-platform'}          # the kit's own scripts are not game text
DISPLAY_NODE_KEYS = ('_name', '_parent', '_active', '_opacity', '_color', '_contentSize', '_anchorPoint', '_trs',
                     '_position', '_scale', '_eulerAngles', '_rotationX', '_rotationY', '_skewX', '_skewY',
                     '_lpos', '_lrot', '_lscale', '_euler', '_layer')
DISPLAY_COMPONENTS = {'cc.Label', 'cc.RichText', 'cc.Sprite', 'cc.Widget', 'cc.Layout', 'cc.UITransform',
                      'cc.UIOpacity', 'cc.LabelOutline', 'cc.LabelShadow', 'cc.Mask', 'cc.Graphics', 'cc.EditBox',
                      'cc.ScrollView', 'cc.PageView', 'cc.ProgressBar', 'cc.Slider', 'cc.Toggle', 'cc.Button',
                      'cc.BlockInputEvents', 'cc.SafeArea', 'cc.Canvas', 'cc.Camera',
                      'sp.Skeleton', 'dragonBones.ArmatureDisplay', 'cc.ParticleSystem', 'cc.ParticleSystem2D'}
VOLATILE_KEYS = {'_id', '_objFlags', '__prefab', 'node', '_prefab', '__editorExtras__', 'fileId', '_enabled'}
CODE_TEXT = _re.compile(r"""\.(?:string|text)\s*=\s*(['"`])((?:\\.|(?!\1).){1,400})\1""")


def _layout_digest(data):
    """sha256 of the display part of one Cocos scene / prefab (list of serialised objects); raw bytes when unparsable."""
    try:
        items = json.loads(data.decode('utf-8-sig'))
    except (UnicodeDecodeError, ValueError):
        return _sha(data)
    if not isinstance(items, list):
        return _sha(data)
    keep = []
    for i, obj in enumerate(items):
        if not isinstance(obj, dict):
            continue
        kind = obj.get('__type__')
        if kind in ('cc.Node', 'cc.PrivateNode'):
            keep.append([i, kind, {k: obj.get(k) for k in DISPLAY_NODE_KEYS if k in obj}])
        elif kind in DISPLAY_COMPONENTS:
            keep.append([i, kind, {k: v for k, v in obj.items() if k not in VOLATILE_KEYS}])
    return _sha(json.dumps(keep, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8'))


def _is_text_table(rel):
    parts = [x.lower() for x in rel.parts]
    name = parts[-1]
    return name.endswith('.json') and (bool(TEXT_TABLE_DIRS & set(parts[:-1])) or name.startswith(TEXT_TABLE_PREFIX))


def display_fingerprints(project):
    """{key: sha256} of the fonts, layout and text under <project>/assets/ (keys: 'font:', 'layout:', 'text:',
    'code-text:' + project-relative posix path). Read only, about a second for a big game."""
    project = Path(project)
    root = project / 'assets'
    out = {}
    if not root.is_dir():
        return out
    for p in sorted(root.rglob('*')):
        if not p.is_file() or p.is_symlink() or p.name.startswith('._'):
            continue
        rel = p.relative_to(project)
        folders = {x.lower() for x in rel.parts[:-1]}
        if SKIP_DIRS & folders:
            continue
        name = p.name.lower()
        try:
            if name.endswith(FONT_SUFFIXES):
                out['font:' + rel.as_posix()] = _sha(p.read_bytes())
            elif name.endswith(LAYOUT_SUFFIXES):
                out['layout:' + rel.as_posix()] = _layout_digest(p.read_bytes())
            elif _is_text_table(rel):
                out['text:' + rel.as_posix()] = _sha(p.read_bytes())
            elif name.endswith(('.js', '.ts')) and not name.endswith('.d.ts') and not (KIT_SCRIPT_DIRS & folders):
                found = sorted(m.group(2) for m in CODE_TEXT.finditer(p.read_text(encoding='utf-8', errors='replace')))
                if found:
                    out['code-text:' + rel.as_posix()] = _sha('\n'.join(found).encode('utf-8'))
        except OSError:
            continue
    return out


DISPLAY_LABEL = {'font': '字体', 'layout': '布局', 'text': '文字表', 'code-text': '脚本里的文字'}


def _display_parts(keys):
    """['布局 2 处：assets/a.prefab、…', …] for the changed / added / removed display keys."""
    groups = {}
    for key in keys:
        kind, _, path = key.partition(':')
        groups.setdefault(kind, []).append(path)
    return ['%s %d 处：%s' % (DISPLAY_LABEL.get(k, k), len(v), _list(v, 5)) for k, v in sorted(groups.items())]


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
    display = display_fingerprints(project)            # 生成时预防 R4M2: text, fonts, layout
    receipt.update(display_schema=DISPLAY_SCHEMA, display=display, display_sha256=images_digest(display))
    from art_production import fingerprint as production_fingerprint
    try:
        production = production_fingerprint(project)
        if production is not None:
            receipt['production_binding'] = production
    except ValueError as exc:
        if status == 'pass':
            raise ValueError('cannot write a passing art receipt: ' + str(exc)) from exc
        receipt['production_binding_error'] = str(exc)
    if isinstance(report.get('base_generated'), dict):
        receipt['base_generated'] = report['base_generated']      # v7.8 H8 / H10 summary (art_records.summary)
    if report.get('capture_round', {}).get('ready'):
        receipt['capture_round'] = {k:report['capture_round'][k] for k in ('round','version','dumps','origin_hash')}
        if status == 'pass':
            receipt['capture_round']['artifact_hash'] = report['capture_round']['artifact_hash']
    if isinstance(report.get('value_presentation'), dict):
        receipt['value_presentation'] = report['value_presentation']
    if isinstance(report.get('maintenance_mapping'), dict):
        receipt['maintenance_mapping'] = report['maintenance_mapping']
        # Provenance only: status still follows all blocking rows; no blanket pass or waiver.
    if isinstance(report.get('english_visual_scope'),dict):receipt['english_visual_scope']=report['english_visual_scope']
    # R4Q3 (补查3 第 3 组): which rows still need fixing, the original-style verdict and Saul's keep record
    receipt['blocking_rows'] = [r.get('check') for r in report.get('rows') or [] if isinstance(r, dict)
                                and r.get('status') == '需处理'][:40]
    if isinstance(report.get('original_style'), dict):
        receipt['original_style'] = report['original_style']
    keep = _keep_record(project)
    if keep:
        receipt['keep_original_style'] = keep
    if note:
        receipt['note'] = note
    _write_json(receipt_path(project), receipt)
    return receipt


def _capture_round_current(project, receipt, capture_build=None):
    from art_round_check import matches_receipt
    try:
        proof = receipt['capture_round']
        root = Path(project) / '.tiktok-kit/art-rounds'
        version = proof['version']
        if not isinstance(version, str) or len(version) != 64 or any(x not in '0123456789abcdef' for x in version):
            return False
        snapshot = json.loads((root/'snapshots'/(version+'.json')).read_text(encoding='utf-8'))
        return matches_receipt(project, capture_build or snapshot['build'], proof)
    except (KeyError, TypeError, ValueError, OSError):
        return False


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


def check(project, board=None, policy=None, capture_build=None):
    """Read-only. -> {'state', 'level' ok|warn|block, 'gate', 'message', 'changed', 'added', 'removed', 'status',
    'board', 'policy', 'strict', 'receipt', 'images_count', 'engine', 'base_audio'}.
    state: no_images | missing | unreadable | not_pass | changed | match_pass | match_3x.
    v7.8 H8: sounds are not in the image receipt, so the sounds are compared with the recorded base here as well
    (art_records.base_audio_now, a hash compare, not an art check): a sound still byte-identical to the base and not in
    docs/art/base-keep.json refuses a new remake game (gate ART_base_audio) and warns otherwise."""
    out = _check_images(project, board, policy, capture_build)
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


def _display_compare(project, receipt, out):
    """生成时预防 R4M2: fill out['display_*']. A receipt from before R4M2 (no `display`) -> display_state unrecorded:
    reported, never refused (the next art_check records it), so the projects in progress keep their receipts."""
    out['display_changed'], out['display_added'], out['display_removed'] = [], [], []
    recorded = receipt.get('display')
    if not isinstance(recorded, dict):
        out['display_state'] = 'unrecorded'
        return
    current = display_fingerprints(project)
    out['display_changed'], out['display_added'], out['display_removed'] = diff(recorded, current)
    moved = out['display_changed'] or out['display_added'] or out['display_removed']
    out['display_state'] = 'changed' if moved else 'match'


def _value_receipt_current(project, receipt, details=None):
    from audit_value_presentation import REVISION, source_fingerprint
    proof = receipt.get('value_presentation') or {}
    current = (proof.get('revision') == REVISION and proof.get('mode') == 'runtime'
            and proof.get('passed') is True and isinstance(proof.get('pages'), int) and proof['pages'] > 0
            and proof.get('source_sha256') == source_fingerprint(project))
    if current:
        return True
    # Approved local changes reuse the immutable old pass plus registered
    # current UI and value evidence; approval alone never bypasses this gate.
    from approved_art_scope import MANIFEST, validate
    if (Path(project) / MANIFEST).is_file():
        try:
            scoped = validate(project, receipt)
        except (KeyError, ValueError, TypeError, OSError, ImportError) as error:
            if details is not None:
                details['approved_local_ui_scope_error'] = str(error)
        else:
            if details is not None:
                details['approved_local_ui_scope'] = scoped
            return True
    return False


def _production_compare(project, receipt, out):
    """Bind production declarations without repeating their pixel checks."""
    from art_production import fingerprint
    try:
        current = fingerprint(project)
    except ValueError as exc:
        out.update(production_state='invalid', production_error=str(exc))
        return False
    recorded = (receipt or {}).get('production_binding')
    declared = current is not None or 'production_binding' in (receipt or {}) or 'production_binding_error' in (receipt or {})
    if not declared:
        out['production_state'] = 'unrecorded'
        return True
    matches = current is not None and recorded == current and 'production_binding_error' not in (receipt or {})
    out['production_state'] = 'match' if matches else 'changed'
    return matches


def _check_images(project, board=None, policy=None, capture_build=None):
    project = Path(project).resolve()
    strict, board, policy = strictness(project, board, policy)
    current = image_fingerprints(project)
    receipt, error = read(project)
    out = {'project': str(project), 'receipt': str(receipt_path(project)), 'board': board, 'policy': policy,
           'strict': strict, 'images_count': len(current), 'changed': [], 'added': [], 'removed': [],
           'status': (receipt or {}).get('status'), 'gate': GATE,
           'display_changed': [], 'display_added': [], 'display_removed': [], 'display_state': None}
    try:
        out['engine'] = engine(project)
    except Exception:  # noqa: BLE001
        out['engine'] = None
    fix = '运行 `art_check.py --project %s --board %s`，全部通过后自动写回执' % (project, board)
    if board == 'localize':
        strict = True  # Receipt only; original-audio policy remains unchanged.
        out['receipt_strict'] = True
    # Explicit user-locked existing-project maintenance is a distinct scoped
    # state, never an invented old/full art pass. Unknown projects stay strict.
    from locked_art_maintenance import MANIFEST as LOCKED_MANIFEST, validate as validate_locked
    if board == 'localize' and capture_build is None and (project/LOCKED_MANIFEST).is_file():
        try:
            locked = validate_locked(project, receipt)
        except (KeyError, ValueError, TypeError, OSError, ImportError) as exc:
            out.update(state='user_locked_art_maintenance_invalid', level='block',
                       locked_art_maintenance_error=str(exc),
                       message='已锁定美术的局部维护证据无效：' + str(exc))
        else:
            out.update(state='user_locked_art_maintenance', level='ok',
                       locked_art_maintenance=locked,
                       message='用户已批准原画面；本轮实际改动、数值、启动及已登记问题证据一致。旧完整美术结果保持原样，不宣称全游戏 ART 通过。')
        return out
    production_current = _production_compare(project, receipt, out)
    if not current and board != 'localize' and production_current:
        out.update(state='no_images', level='ok', message='工程 assets/ 下没有图片，没有美术要核对')
        return out
    if receipt is None:
        out.update(state='unreadable' if error else 'missing')
        why = '美术检查回执 %s %s' % (out['receipt'], '读不了（%s）' % error if error else '不存在')
    else:
        out['changed'], out['added'], out['removed'] = diff(receipt['images'], current)
        moved = out['changed'] or out['added'] or out['removed']
        status = receipt.get('status')
        _display_compare(project, receipt, out)          # 生成时预防 R4M2
        display_moved = out['display_changed'] or out['display_added'] or out['display_removed']
        if not production_current:
            out['state'] = 'production_binding_stale'
            why = '制作素材、配方、图文内区/应查状态或制作规则已变；旧美工回执不能沿用'
            if out.get('production_error'):
                why += '：' + out['production_error']
        elif moved:
            parts = []
            for label, key in (('改了', 'changed'), ('新增', 'added'), ('删了', 'removed')):
                if out[key]:
                    parts.append('%s %d 张：%s' % (label, len(out[key]), _list(out[key])))
            out['state'] = 'changed'
            why = '回执（%s，%s）之后图片变了，%s' % (status, receipt.get('created'), '；'.join(parts))
        elif display_moved:
            parts = []
            for label, key in (('改了', 'display_changed'), ('新增', 'display_added'), ('删了', 'display_removed')):
                if out[key]:
                    parts.append('%s%s' % (label, '、'.join(_display_parts(out[key]))))
            out['state'] = 'display_changed'
            why = '回执（%s，%s）之后画面上的文字、字体或布局变了，%s' % (status, receipt.get('created'), '；'.join(parts))
        elif board == 'localize' and not _value_receipt_current(project, receipt, out):
            out['state'] = 'value_evidence_stale'
            why = '缺分数/奖励实际页面验收，或文字代码、字体、坐标、绑定已变；旧图片回执不能放行'
        elif board == 'localize' and status == 'pass' and (
                capture_build is not None or (Path(project)/'docs/art/capture-plan.json').exists() or
                (Path(project)/'.tiktok-kit/art-rounds/current.json').exists()) and not _capture_round_current(project, receipt, capture_build):
            out['state'] = 'capture_round_stale'
            why = '本轮截图、工程或 Web 导出身份已变；按重拍清单补采并运行完整美工检查'
        elif status == 'pass':
            out.update(state='match_pass', level='ok',
                       message='美术回执对得上：art_check 通过（%s），%d 张图未改%s' % (
                           receipt.get('created'), len(current),
                           '，文字、字体、布局未改' if out['display_state'] == 'match' else
                           '（旧回执没记文字、字体、布局，下次 art_check 补上）'))
            kept = receipt.get('original_style') or {}
            if kept.get('state') == 'kept_original':      # R4Q3: say which pictures were kept and who decided
                who = receipt.get('keep_original_style') or {}
                out['message'] += '；原图保留 %d 张（大块深色/纯色不适用%s）' % (
                    len(kept.get('original') or []), '，%s %s 定的' % (who.get('decided_by'), who.get('date')) if who else '')
            if out.get('approved_local_ui_scope'):
                out['state'] = 'approved_local_ui_scope'
                out['message'] += '；本轮已批准局部UI及数值证据合并核验通过，旧全局通过回执保持原样（不是新全游戏ART-06）'
            return out
        elif status == 'fail' and board == 'localize' and _kept_by_record(project, receipt):
            # R4Q3: the only row left is 大块深色与纯色底, the original pictures could not be told from new ones (no
            # original record / no Pillow), and Saul's keep_original_style.json says keep the original art: the
            # record stands in for the hand-written authorization the sessions used to need. Warn, never block.
            keep = _keep_record(project)
            out.update(state='kept_original_record', level='warn', gate=GATE_KEEP,
                       message='保留原画风（%s %s 定的，%s）：回执里只剩「大块深色与纯色底」这一行，分不清原图和新图（%s），'
                       '按记录放行并警告；补上原包登记（raw_inputs.py keep 或 art_records.py base）后重跑 art_check' % (
                           keep.get('decided_by'), keep.get('date'), KEEP_RECORD.as_posix(),
                           (receipt.get('original_style') or {}).get('state')))
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
    scope = ('英化游戏，不出包、不起试玩' if board == 'localize' else '重塑新游戏，不出包、不起试玩') if strict else '旧游戏只警告'
    out['message'] = '%s（%s）：%s；%s' % (RERUN, scope, why, fix)
    return out


def finding(result):
    """The check() result as a tiktok_finalize finding (id, level, message, evidence) or None when ok."""
    if result['level'] == 'ok':
        return None
    evidence = {k: result.get(k) for k in ('state', 'status', 'board', 'policy', 'receipt')}
    evidence.update({k: result[k][:50] for k in ('changed', 'added', 'removed')})
    evidence['base_audio'] = list(result.get('base_audio') or [])[:50]
    evidence['display_state'] = result.get('display_state')            # 生成时预防 R4M2
    evidence.update({k: list(result.get(k) or [])[:50] for k in ('display_changed', 'display_added', 'display_removed')})
    return {'id': result['gate'], 'level': 'block' if result['level'] == 'block' else 'warn',
            'message': result['message'], 'evidence': evidence}


ROW = {'no_images': '没有图片，不用核对', 'match_pass': '对得上（art_check 通过）', 'match_3x': '3.x 未覆盖（不是通过）',
       'approved_local_ui_scope': '原美术未变，已批准局部UI与数值证据合并通过（非新全游戏ART-06）',
       'user_locked_art_maintenance': '用户批准的美术已锁定；局部维护证据有效（非全游戏ART通过）',
       'user_locked_art_maintenance_invalid': '已锁定美术的局部维护证据无效',
       'missing': '没有回执', 'unreadable': '回执读不了', 'not_pass': '回执不是通过', 'changed': '图片改过',
       'display_changed': '文字、字体或布局改过',   # display_changed: 生成时预防 R4M2
       'kept_original_record': '保留原画风（按 keep_original_style.json 放行，警告）'}   # R4Q3


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
    out['display_state'] = result.get('display_state')                 # 生成时预防 R4M2
    out.update({k: list(result.get(k) or [])[:20] for k in ('display_changed', 'display_added', 'display_removed')})
    out['message'] = result.get('message')
    for key in ('approved_local_ui_scope', 'approved_local_ui_scope_error', 'locked_art_maintenance', 'locked_art_maintenance_error'):
        if key in result:
            out[key] = result[key]
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
    # 生成时预防 R4M2: display (text, fonts, layout) is carried only when it was recorded and matched before this run
    display_now = display_fingerprints(project) if isinstance(receipt.get('display'), dict) and \
        before.get('display_state') == 'match' else None
    dmoved = diff(receipt['display'], display_now) if display_now is not None else ([], [], [])
    if not (changed or added or removed or any(dmoved)):
        return receipt
    entry = {'by': by, 'time': dt.datetime.now().astimezone().isoformat(timespec='seconds'),
             'changed': changed[:200], 'added': added[:200], 'removed': removed[:200],
             'why': 'the receipt matched every image before this run; only this run changed these files'}
    if any(dmoved):
        entry.update(display_changed=dmoved[0][:200], display_added=dmoved[1][:200], display_removed=dmoved[2][:200])
        receipt['display'] = display_now
        receipt['display_sha256'] = images_digest(display_now)
    receipt['carried'] = list(receipt.get('carried') or []) + [entry]
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
