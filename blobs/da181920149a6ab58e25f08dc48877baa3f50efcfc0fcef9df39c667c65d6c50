#!/usr/bin/env python3
"""出包后返工只查改动涉及的部分（简化.11.15，Saul 2026-11-04）。

Saul 2026-11-04：「当一切检查通过出测试包之后，还发现了问题，需要重新回去把这个最新的测试包进行修改的时候，她明明只需要
修改一个点，但是修改完了之后又跑了一遍很久的测试……比如我修改了贴图，之后出包甚至又要检查一遍音频，这种情况不要发生，要让
对应的ai记住检查过哪些内容，哪些是新修改的地方，出包后的返工修改，就只检查修改涉及的那些部分」。

The package about to be written is compared, file by file, with the last package that passed: an official writer wrote it
(its receipt matches its bytes) and the receipt keeps the record of the two browser regressions it passed (check_package
REUSE_SCHEMA). Every changed file is put in one kind:

  code       .js .mjs .cjs .wasm (game, adapter, engine, every bundle's index.js)
  config     root files (game.json, project.config.json ...) and every bundle config.json
  structure  import JSON that defines anything but pictures, sounds and fonts (prefabs, scenes, animations, materials ...)
             or that cannot be read; packed 3.x .cconb
  data       other JSON (JsonAsset tables, settings.json ...)
  image      pictures (.png .jpg .webp .pkm .astc), .plist atlases and import JSON with only cc.SpriteFrame / cc.Texture2D /
             cc.SpriteAtlas / cc.ImageAsset / cc.ParticleAsset
  audio      .mp3 .ogg .wav .m4a .aac and import JSON with only cc.AudioClip
  font       .ttf .otf .woff .fnt and import JSON with only cc.BitmapFont / cc.TTFFont / cc.LabelAtlas
  other      anything else

Writer reuse (both writers, check_package.check / writer_regressions with rework_of): when every changed file is image,
audio or font AND the adapter file, both check tools, the engine, policy, board and the required suites are the same as
in the old record, only the browser checks that can see such a change run again:
  image, font  layout_state, button_sweep, image_stall, dead_shell, ad_entries (pixels and node boxes)
  audio        layout_state (startup download, sound before the home page)
  a changed file in a bundle loaded before the home page (layout_state startup_measured.beforeHome, plus main and
  internal; all bundles when the old record has no measurement) also: startup, startup3x, network
Everything else keeps the old pass, with its receipt named (reused_from): the rewarded-ad regression (10 cases),
ad_outcome, save_restart, resume_play, frame_rate, popin. A suite that runs again also runs the suites its sidecar names
in "after". Anything else (code, config, structure, data, other, a different adapter or tool, no official old package):
every browser check runs, as before, and the reason is printed. Static checks (package gates, ZIP verifier, startup
closure, packed assets, finalize, art receipt) always run: they take seconds.

What the AI itself re-checks is in the same plan (ai.todo / ai.skip): a picture change re-checks the pages that use it,
the Chinese check (incremental) and the image review of those pictures; it does not re-listen to sound, re-test saves,
the ad flow, slow network, 60/120 Hz, touch or the platform entries. A code change re-checks the feature that changed.

  rework_scope.py --old <上一个交付包.zip 或出包文件夹> (--native <新 Native 目录> --project <工程> | --new <新包.zip>)
                  [--project <工程>] [--app-id <App ID>] [--ad-regression <适配文件>] [--board localize]
                  [--policy new|legacy] [--json]

--old <文件夹> reads that folder's 最新.txt (written by the writers). --native is the preview before packaging: the writers
run tiktok_finalize.finalize_native on the build folder before anything else (platform parts, App ID, PNG compression),
so a raw Creator build differs from the delivered package in its code and most PNGs. The preview runs the same step on a
temporary copy (about 2 s; the build folder is not touched; App ID from --app-id or the old package, board and options
from the project's source record), so it plans what the writer will plan. With --project the plan is also written to
<project>/docs/checks/rework-<time>.json (the record the next AI reads); the writers write one themselves after
publishing (record_for_writer), and theirs is the one that counts. Exit 0 with a plan (reuse or not); 2 usage error or a
build that finalize refuses. Standard library only; Python 3.9 compatible.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHARED = HERE.parents[2] / 'remake-core' / 'scripts'
for _p in (HERE, SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

SCHEMA = 'rework-reuse.v1'
REUSE_SCHEMA = 'writer-regressions.v1'          # check_package.REUSE_SCHEMA (the receipt's regression record)
LATEST = '最新.txt'
LATEST_MARK = '# 最新包（写包入口自动写'
OLD_FOLDER = '旧包'
MD5 = re.compile(r'\.[0-9a-f]{5}(?=\.[A-Za-z0-9]+$)')
UUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
CODE_EXT = {'.js', '.mjs', '.cjs', '.wasm'}
IMAGE_EXT = {'.png', '.jpg', '.jpeg', '.webp', '.pkm', '.astc', '.bmp', '.gif', '.plist'}
AUDIO_EXT = {'.mp3', '.ogg', '.wav', '.m4a', '.aac'}
FONT_EXT = {'.ttf', '.otf', '.woff', '.woff2', '.fnt'}
RESOURCE_CLASSES = {
    'cc.SpriteFrame': 'image', 'cc.Texture2D': 'image', 'cc.SpriteAtlas': 'image', 'cc.ImageAsset': 'image',
    'cc.ParticleAsset': 'image',
    'cc.AudioClip': 'audio',
    'cc.BitmapFont': 'font', 'cc.TTFFont': 'font', 'cc.LabelAtlas': 'font',
}
DATA_CLASSES = {'cc.JsonAsset', 'cc.TextAsset'}
RESOURCE_KINDS = ('image', 'audio', 'font')
KIND_LABEL = {'code': '代码', 'config': '设置和分包清单', 'structure': '页面结构（预制体、场景、动画等）', 'data': '数据表',
              'image': '图片', 'audio': '音频', 'font': '字体', 'other': '其他文件'}
VISUAL = ('layout_state', 'button_sweep', 'image_stall', 'dead_shell', 'ad_entries')
STARTUP = ('startup', 'startup3x', 'network')
RERUN = {'image': VISUAL, 'font': VISUAL, 'audio': ('layout_state',)}
ALWAYS_BEFORE_HOME = ('main', 'internal')
# What the AI checks by hand after a change (the plan's ai.todo / ai.skip). kinds: the changes that call for it.
AI_CHECKS = (
    ('art', '页面美工：用到改动的页面在两种手机尺寸截图看图、对这几页跑 art_check（不重做全部页面）',
     {'image', 'font', 'structure'}),
    ('chinese', '中文专项检查（只识新加和改过的图，本来就是增量）', {'image', 'font', 'structure', 'code', 'data'}),
    ('image_review', '图片复核记录：只补改过的图', {'image'}),
    ('click', '改过的页面上的按钮和弹窗开关真实点一遍', {'structure'}),
    ('audio', '改过的音效、音乐实际播一次；设置里音效、音乐开关和音量还管用', {'audio'}),
    ('feature', '这次改的功能就地验证：回复里写清改了哪个功能、怎么验的、为什么别处不受影响', {'code', 'data', 'config', 'other'}),
    ('start', '冷启动进首页、开一局', {'code', 'config', 'other'}),
)
NOT_AGAIN = ('音效和音乐', '存档关掉重开', '广告流程（看完、取消、失败、超时）', '慢网和加载失败 Retry', '60/120 帧手感',
             '触摸坐标', '加桌面、主页回访', '其余页面的美工')
AI_SKIP_BY_KIND = {          # the hand checks a change of only these kinds never calls for
    'image': NOT_AGAIN[:7] + ('没用到改动图片的页面的美工',),
    'font': NOT_AGAIN[:7] + ('没用到这个字体的页面的美工',),
    'audio': NOT_AGAIN[1:],
}


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _sha_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for block in iter(lambda: fh.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


# ---------------------------------------------------------------- the old package

def find_latest(folder):
    """-> (zip path or None, note). The ZIP 最新.txt in `folder` names (the writers write it); a renamed copy of the same
    bytes in the folder or its 旧包/ is found by the sha256 that 最新.txt records. No 最新.txt -> None (never a guess)."""
    folder = Path(folder)
    latest = folder / LATEST
    try:
        text = latest.read_text(encoding='utf-8')
    except OSError:
        return None, 'no %s in %s: no earlier package to compare with, every check runs' % (LATEST, folder)
    if not text.startswith(LATEST_MARK):
        return None, '%s was not written by a writer: every check runs' % latest
    named = re.search(r'^上传 TikTok 用这个：(.+?)\s*$', text, re.M)
    sha = re.search(r'^sha256：([0-9a-f]{64})\s*$', text, re.M)
    if not sha:
        return None, '%s has no sha256 line: every check runs' % latest
    want = sha.group(1)
    size = re.search(r'^大小：(\d+) 字节\s*$', text, re.M)
    size = int(size.group(1)) if size else None
    candidates = []
    if named:
        candidates.append(Path(named.group(1)))
    for where in (folder, folder / OLD_FOLDER):
        try:
            candidates.extend(sorted(where.glob('*.zip')))
        except OSError:
            pass
    seen = set()
    for cand in candidates:
        key = str(cand)
        if key in seen:
            continue
        seen.add(key)
        try:
            if not cand.is_file() or cand.is_symlink() or (size is not None and cand.stat().st_size != size):
                continue
            if _sha_file(cand) == want:
                return cand, 'the package %s names (%s)' % (LATEST, cand.name)
        except OSError:
            continue
    return None, 'the package %s names (sha256 %s...) is not in %s or %s/: every check runs' % (
        LATEST, want[:12], folder, OLD_FOLDER)


def resolve(arg, out=None):
    """--rework-of value -> (old ZIP path or None, note). 'none' / '' -> None; 'auto' -> 最新.txt of the folder `out` is
    written into; a folder -> its 最新.txt; a file -> that ZIP."""
    if arg is None:
        return None, 'rework reuse off'
    text = str(arg).strip()
    if text.lower() in ('', 'none', 'off', 'no'):
        return None, 'rework reuse off (--rework-of none): every check runs'
    if text.lower() == 'auto':
        if out is None:
            return None, 'rework reuse: no output folder known, every check runs'
        return find_latest(Path(out).resolve().parent)
    path = Path(text).expanduser()
    if path.is_dir():
        return find_latest(path)
    if path.is_file():
        return path, 'given with --rework-of'
    return None, '--rework-of %s does not exist: every check runs' % text


def read_zip(path):
    """{name: bytes} of a ZIP (directories left out; every member is read, so a bad CRC raises)."""
    with zipfile.ZipFile(path) as z:
        return {i.filename: z.read(i) for i in z.infolist() if not i.is_dir()}


def official_record(old_zip, old_files=None):
    """-> (receipt path, receipt dict, problem or None). Official = a writer receipt for exactly these ZIP bytes
    (verify_native_zip.receipt_status) whose regression record has both parts passed or not applicable."""
    import verify_native_zip as vnz
    old_zip = Path(old_zip)
    data = old_zip.read_bytes()
    zip_sha = _sha(data)
    files = old_files if old_files is not None else read_zip(old_zip)
    status = vnz.receipt_status(old_zip, zip_sha, {n: _sha(b) for n, b in files.items()})
    receipt_path = status.get('receipt')
    if status.get('entry') != 'official':
        return receipt_path, None, 'old package %s is not official: %s' % (old_zip.name, status.get('entry_reason'))
    try:
        receipt = json.loads(Path(receipt_path).read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        return receipt_path, None, 'old receipt unreadable: %s' % error
    record = receipt.get('regressions') if isinstance(receipt, dict) else None
    if not isinstance(record, dict) or record.get('schema') != REUSE_SCHEMA:
        return receipt_path, None, ('old receipt %s has no regression record (written before v7.9, or a regression did '
                                    'not pass there)' % Path(receipt_path).name)
    for key in ('rewarded_ad_regression', 'runtime_regression'):
        part = record.get(key)
        if not isinstance(part, dict) or part.get('status') not in ('passed', 'not_applicable'):
            return receipt_path, None, 'old receipt: %s did not pass' % key
    return receipt_path, receipt, None


# ---------------------------------------------------------------- what changed

def bundle_of(name):
    parts = name.split('/')
    if len(parts) >= 3 and parts[0] in ('assets', 'subpackages', 'remote'):
        return parts[1]
    return '(root)'


def import_classes(doc):
    """Class names an import JSON defines (Cocos compiled format: element 3 is the shared class list; the Texture2D pack
    {"type": ..., "data": ...}; plain objects with __type__). [] when nothing can be read."""
    if isinstance(doc, dict):
        if isinstance(doc.get('type'), str) and 'data' in doc:
            return [doc['type']]
        return [doc['__type__']] if isinstance(doc.get('__type__'), str) else []
    if not isinstance(doc, list):
        return []
    if len(doc) > 3 and isinstance(doc[3], list) and (not doc or isinstance(doc[0], (int, float))):
        out = []
        for entry in doc[3]:
            if isinstance(entry, str):
                out.append(entry)
            elif isinstance(entry, list) and entry and isinstance(entry[0], str):
                out.append(entry[0])
        return out
    return [item['__type__'] for item in doc if isinstance(item, dict) and isinstance(item.get('__type__'), str)]


def kinds_of(name, data):
    """The kinds of one file's content (a set: an import pack can define pictures and fonts)."""
    low = name.lower()
    ext = os.path.splitext(low)[1]
    if ext in CODE_EXT:
        return {'code'}
    if '/' not in name:
        return {'config'}
    if ext in IMAGE_EXT:
        return {'image'}
    if ext in AUDIO_EXT:
        return {'audio'}
    if ext in FONT_EXT:
        return {'font'}
    if ext == '.cconb':
        return {'structure'}
    if ext == '.json':
        if '/import/' in low:
            try:
                classes = import_classes(json.loads(data.decode('utf-8-sig')))
            except (UnicodeDecodeError, ValueError):
                return {'structure'}
            if not classes:
                return {'structure'}
            if set(classes) <= DATA_CLASSES:
                return {'data'}
            kinds = {RESOURCE_CLASSES.get(c) for c in classes}
            if None in kinds:
                return {'structure'}
            return set(kinds)
        if re.search(r'(^|/)config(\.[0-9a-f]{5})?\.json$', low):
            return {'config'}
        return {'data'}
    return {'other'}


def diff(old_files, new_files):
    """old/new {name: bytes} -> {'changed': [...], 'added': [...], 'removed': [...], 'kinds': {kind: [names]},
    'bundles': [...]} ; names are compared without the 5-hex md5 suffix (md5Cache builds)."""
    def by_key(files):
        out = {}
        for name, data in files.items():
            out.setdefault(MD5.sub('', name), []).append((name, data))
        return out
    a, b = by_key(old_files), by_key(new_files)
    changed = sorted(k for k in b if k in a and sorted(_sha(d) for _, d in a[k]) != sorted(_sha(d) for _, d in b[k]))
    added, removed = sorted(k for k in b if k not in a), sorted(k for k in a if k not in b)
    kinds = {}
    for key in changed + added + removed:
        both = set()
        for _, data in a.get(key, []) + b.get(key, []):
            both |= kinds_of(key, data)
        for kind in both:
            kinds.setdefault(kind, []).append(key)
    return {'changed': changed, 'added': added, 'removed': removed, 'kinds': kinds,
            'bundles': sorted({bundle_of(k) for k in changed + added + removed})}


# ---------------------------------------------------------------- the plan

def _adapter_path(adapter):
    import ad_regression as ad
    return adapter or os.environ.get(ad.ENV_ADAPTER) or None


def _closure(names, rerun, catalog):
    """rerun plus the suites they run "after" (their evidence is passed on), within names."""
    out, todo = set(rerun), list(rerun)
    while todo:
        for dep in catalog.get(todo.pop(), {}).get('after', []) or []:
            if dep in names and dep not in out:
                out.add(dep)
                todo.append(dep)
    return out


def plan(old_zip, new_files, adapter=None, policy=None, board=None):
    """Writer reuse plan for the package `new_files` ({name: bytes}) against the last passed package `old_zip`.
    -> {'schema', 'reuse': bool, 'why', 'old': {...}, 'changes': {...}, 'required', 'rerun', 'reused', 'ad', ...}.
    Never raises for a reuse problem: reuse False with the reason (every check then runs)."""
    if os.environ.get('DEBRAND_DELTA_SCOPE'):
        import importlib.util
        import sys
        file = Path(__file__).with_name('debrand_reuse_plan.py')
        spec = importlib.util.spec_from_file_location('_scoped_debrand_plan', file)
        helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
        # Supply this module's already authenticated generic helpers.
        class Base: pass
        api = Base()
        for key in ('read_zip','official_record','_adapter_path','_closure','diff','summary_of_changes','_sha_file','SCHEMA'):
            setattr(api,key,globals()[key])
        return helper.plan(api, old_zip, new_files, adapter, policy, board)
    import ad_regression as ad
    import runtime_regression as rr
    out = {'schema': SCHEMA, 'reuse': False, 'why': None, 'old': {'zip': str(old_zip)}, 'changes': None,
           'required': None, 'rerun': None, 'reused': [], 'ad': 'run', 'records': None}

    scoped = bool(os.environ.get('PLAY_ART_DELTA_SCOPE'))
    def no(why):
        if scoped:
            raise ValueError('scoped PLAY reuse refused: '+why)
        out['why'] = why
        return out
    try:
        old_zip = Path(old_zip)
        old_files = read_zip(old_zip)
        out['old'].update(zip_sha256=_sha_file(old_zip), name=old_zip.name)
        receipt_path, receipt, problem = official_record(old_zip, old_files)
        out['old']['receipt'] = str(receipt_path) if receipt_path else None
        if receipt is not None:
            out['old']['written'] = receipt.get('created')
            out['old']['tool'] = receipt.get('tool')
        changes = diff(old_files, new_files)
        out['changes'] = summary_of_changes(changes)
        if problem:
            return no(problem)
        record = receipt['regressions']
        old_ad, old_rt = record['rewarded_ad_regression'], record['runtime_regression']
        out['records'] = {'rewarded_ad_regression': old_ad, 'runtime_regression': old_rt}
        optional_art_delta = None
        if scoped:
            import importlib.util
            gp = Path(__file__).with_name('play_art_delta_guard.py')
            gs = importlib.util.spec_from_file_location('_play_art_delta_guard', gp)
            gm = importlib.util.module_from_spec(gs); gs.loader.exec_module(gm)
            optional_art_delta = gm.validate(old_zip, new_files, _adapter_path(adapter))
            out['optional_art_delta'] = optional_art_delta
        browser_policy_equivalence = None
        if optional_art_delta and (old_ad.get('tool_sha256') != ad.tool_digest() or old_rt.get('tool_sha256') != rr.tool_digest(rr.load_suites())):
            ep = Path(__file__).with_name('browser_policy_tool_equivalence.py')
            es = importlib.util.spec_from_file_location('_browser_policy_equivalence', ep)
            em = importlib.util.module_from_spec(es); es.loader.exec_module(em)
            project = json.loads(Path(optional_art_delta['scope']['path']).read_text())['project']
            browser_policy_equivalence = em.validate(project, old_ad.get('tool_sha256'), old_rt.get('tool_sha256'))
            out['browser_policy_tool_equivalence'] = browser_policy_equivalence
        blocking = [] if optional_art_delta else [k for k in changes['kinds'] if k not in RESOURCE_KINDS]
        if blocking:
            first = changes['kinds'][blocking[0]][:3]
            return no('changed %s (%s): every browser check runs' % (
                ', '.join(sorted(blocking)), ', '.join(first)))
        adapter = _adapter_path(adapter)
        adapter_sha = _sha_file(adapter) if adapter and Path(adapter).is_file() else None
        needs_ad = ad.needs_regression(new_files)
        if needs_ad:
            if old_ad.get('status') != 'passed':
                return no('the old package had no rewarded-ad regression; this one needs it')
            if adapter_sha is None or (old_ad.get('adapter_sha256') != adapter_sha and not optional_art_delta):
                return no('adapter differs from the one the old package passed with (rewarded-ad regression)')
            if old_ad.get('tool_sha256') != ad.tool_digest() and not browser_policy_equivalence:
                return no('rewarded-ad regression tool differs from the one the old package passed with')
        elif old_ad.get('status') != 'not_applicable':
            return no('old rewarded-ad record does not fit this package')
        if 'game.js' not in new_files:
            return no('no game.js in the new package')
        if old_rt.get('status') != 'passed':
            return no('the old package had no runtime regression')
        catalog = rr.load_suites()
        names = rr.required_suites(new_files, adapter, catalog)
        out['required'] = list(names)
        if adapter_sha is None or (old_rt.get('adapter_sha256') != adapter_sha and not optional_art_delta):
            return no('adapter differs from the one the old package passed with (runtime regression)')
        if old_rt.get('tool_sha256') != rr.tool_digest(catalog) and not browser_policy_equivalence:
            return no('runtime regression tools differ from the ones the old package passed with')
        if sorted(old_rt.get('required') or []) != sorted(names):
            return no('the runtime suites this package needs differ from the ones the old package ran')
        judged = rr.package_policy(new_files, policy)[0]
        if old_rt.get('policy') != judged:
            return no('the old package was checked as a %s game; this one is judged %s' % (old_rt.get('policy'), judged))
        if (old_rt.get('board') or None) != ((board if board in rr.BOARDS else None)):
            return no('board differs from the old package (%s / %s)' % (old_rt.get('board'), board))
        adapter_data = rr.load_adapter(adapter, catalog)
        engine = rr.detect_engine(new_files, adapter_data)
        if old_rt.get('engine') and old_rt.get('engine') != engine:
            return no('engine differs from the old package')
        passed = {r.get('suite') for r in old_rt.get('suites') or [] if isinstance(r, dict) and r.get('passed') is True}
        if not set(names) <= passed:
            return no('the old record does not show every required suite passed')
        measured = old_rt.get('startup_measured') if isinstance(old_rt.get('startup_measured'), dict) else None
        before = set(measured.get('beforeHome') or []) | set(ALWAYS_BEFORE_HOME) if measured else None
        rerun = set(optional_art_delta['rerun']) if optional_art_delta else set()
        if not optional_art_delta:
            for kind in changes['kinds']:
                rerun |= set(RERUN[kind])
        if set(changes['kinds']) & {'image', 'font'} and any(
                isinstance(entry, dict) and entry.get('role') == 'revive' for entry in (adapter_data.get('ad_entries') or [])):
            rerun.add('ad_outcome')
        startup_hit = [b for b in changes['bundles'] if before is None or b in before]
        if startup_hit:
            rerun |= set(STARTUP)
        rerun = _closure(names, {n for n in rerun if n in names}, catalog)
        out.update(reuse=True, why=None, rerun=[n for n in names if n in rerun],
                   reused=[n for n in names if n not in rerun], ad='reuse' if needs_ad else 'not_applicable',
                   before_home=sorted(before) if before is not None else None, startup_hit=startup_hit)
        return out
    except Exception as error:  # noqa: BLE001
        if scoped:
            raise ValueError('scoped PLAY reuse refused (%s: %s)' % (type(error).__name__, error)) from error
        return no('rework plan failed (%s: %s): every check runs' % (type(error).__name__, error))


def summary_of_changes(changes):
    return {'changed': len(changes['changed']), 'added': len(changes['added']), 'removed': len(changes['removed']),
            'kinds': {k: {'count': len(v), 'files': v[:20]} for k, v in sorted(changes['kinds'].items())},
            'bundles': changes['bundles']}


def public(p):
    """The plan without the old records (what receipts, reports and docs/checks/ keep)."""
    if not isinstance(p, dict):
        return None
    return {k: v for k, v in p.items() if k != 'records'}


# ---------------------------------------------------------------- results for check_package

def reused_ad(p):
    """The old rewarded-ad pass, for a reuse plan."""
    old = dict(p['records']['rewarded_ad_regression'])
    old.update(id='rewarded_ad_regression', reused_from=p['old'].get('receipt'), seconds=0.0,
               note='reused: only %s changed since %s (出包后返工，Saul 2026-11-04)' % (
                   kinds_text(p), p['old'].get('name')))
    return old


def to_rerun(p, names):
    """The required suites of this package that run again, in catalogue order."""
    return [n for n in names if n in set(p.get('rerun') or [])]


def merge_runtime(p, summary, names):
    """One runtime summary for the receipt: the suites that ran again (summary, or None when none ran) plus the old passes
    of the rest, each row marked reused_from."""
    import runtime_regression as rr
    old = p['records']['runtime_regression']
    receipt = p['old'].get('receipt')
    rows = {}
    for row in (summary or {}).get('suites') or []:
        if isinstance(row, dict):
            rows[row.get('suite')] = row
    reused = [n for n in names if n not in rows]
    for name in reused:
        rows[name] = {'suite': name, 'passed': True, 'problems': [], 'cases': [], 'warnings': [], 'evidence': None,
                      'seconds': 0.0, 'browser': False, 'reused_from': receipt}
    warnings = list((summary or {}).get('warnings') or [])
    warnings += [w for w in old.get('warnings') or [] if any(str(w).startswith(n + ':') for n in reused)]
    catalog = rr.load_suites()
    return {'id': 'runtime_regression', 'status': 'passed', 'passed': True,
            'engine': (summary or {}).get('engine') or old.get('engine'),
            'suites': [rows[n] for n in names], 'required': list(names),
            # a suite kept from the old package is not "not run" (the rerun used --suites, which lists the rest so)
            'not_run': [r for r in (summary or {}).get('not_run') or [] if r.get('suite') not in reused],
            'board': (summary or {}).get('board', old.get('board')),
            'problems': [], 'policy': (summary or {}).get('policy') or old.get('policy'),
            'policy_reason': (summary or {}).get('policy_reason'),
            'startup_measured': (summary or {}).get('startup_measured') or old.get('startup_measured'),
            'warnings': warnings,
            'tool_sha256': (summary or {}).get('tool_sha256') or rr.tool_digest(catalog),
            'adapter_sha256': (summary or {}).get('adapter_sha256') or old.get('adapter_sha256'),
            'seconds': (summary or {}).get('seconds', 0.0),
            'rework': {'reran': [n for n in names if n not in reused], 'reused': reused, 'reused_from': receipt,
                       'old_zip': p['old'].get('name'), 'changed': kinds_text(p),
                       **({'optional_art_delta': p['optional_art_delta']} if p.get('optional_art_delta') else {}),
                       **({'browser_policy_tool_equivalence':p['browser_policy_tool_equivalence']} if p.get('browser_policy_tool_equivalence') else {}),
                       **({'debrand_delta':p['debrand_delta']} if p.get('debrand_delta') else {})}}


# ---------------------------------------------------------------- plain words

def kinds_text(p):
    kinds = ((p or {}).get('changes') or {}).get('kinds') or {}
    if not kinds:
        return '没有文件变化'
    return '、'.join('%s %d 个' % (KIND_LABEL.get(k, k), v['count']) for k, v in kinds.items())


def ai_checks(p):
    """-> (todo, skip): the hand checks this change calls for, and the ones it does not."""
    kinds = set((((p or {}).get('changes') or {}).get('kinds') or {}).keys())
    todo = [text for _, text, need in AI_CHECKS if kinds & need]
    if not kinds:
        return [], ['全部：和上一个交付包一字不差，不用再查']
    if kinds <= set(RESOURCE_KINDS):
        present = [k for k in RESOURCE_KINDS if k in kinds]
        common = set.intersection(*(set(AI_SKIP_BY_KIND[k]) for k in present))
        ordered = [s for k in present for s in AI_SKIP_BY_KIND[k]]
        return todo, list(dict.fromkeys(s for s in ordered if s in common))
    return todo, ['和这次改的功能无关的：' + '、'.join(NOT_AGAIN) + '（只有这次改的代码就是它们时才查，回复里写明为什么查）']


def describe(p, pages=None):
    """Plain-Chinese lines for the AI's reply and the writer's output."""
    if not isinstance(p, dict):
        return []
    old = p.get('old') or {}
    lines = ['返工范围｜和上一个交付包 %s 比：' % (old.get('name') or old.get('zip'))]
    lines.append('- 改了：%s' % kinds_text(p))
    for kind, v in sorted((((p.get('changes') or {}).get('kinds')) or {}).items()):
        lines.append('  · %s：%s%s' % (KIND_LABEL.get(kind, kind), '、'.join(v['files'][:5]),
                                       ' 等 %d 个' % v['count'] if v['count'] > 5 else ''))
    if pages:
        lines.append('- 用到改动的页面：' + '、'.join(pages[:12]) + (' 等 %d 个' % len(pages) if len(pages) > 12 else ''))
    lines.append('- 每次都跑：静态检查和 ZIP 核对（几秒）')
    if p.get('reuse'):
        lines.append('- 写包时重跑：' + ('、'.join(p.get('rerun') or []) or '没有（浏览器检查全部沿用）'))
        reused = list(p.get('reused') or [])
        if p.get('ad') == 'reuse':
            reused = ['激励广告回归 10 例'] + reused
        lines.append('- 沿用上一个包的通过结果：' + ('、'.join(reused) or '没有'))
    else:
        lines.append('- 写包时：浏览器检查全部照跑（%s）' % (p.get('why') or '没有可比的上一个包'))
    todo, skip = ai_checks(p)
    if todo:
        lines.append('- 你（AI）自己要查的：' + '；'.join(todo))
    if skip:
        lines.append('- 不用再查的：' + '；'.join(skip))
    return lines


# ---------------------------------------------------------------- project side (pages, record)

def uuid_index(project):
    """{uuid: asset path relative to the project} from every .meta under assets/ (sub-assets included)."""
    index = {}
    root = Path(project) / 'assets'
    for meta in sorted(root.rglob('*.meta')) if root.is_dir() else []:
        try:
            doc = json.loads(meta.read_text(encoding='utf-8-sig'))
        except (OSError, ValueError):
            continue
        rel = meta.relative_to(project).as_posix()[:-5]
        stack = [doc]
        while stack:
            item = stack.pop()
            if isinstance(item, dict):
                uid = item.get('uuid')
                if isinstance(uid, str):
                    index.setdefault(uid.split('@')[0], rel)
                    index.setdefault(uid, rel)
                stack.extend(item.values())
            elif isinstance(item, list):
                stack.extend(item)
    return index


def affected_pages(project, p):
    """Prefabs and scenes of the project that reference a changed picture, sound or font (by uuid). Best effort."""
    files = []
    for v in ((((p or {}).get('changes') or {}).get('kinds')) or {}).values():
        files.extend(v['files'])
    uuids = {m.group(0) for f in files for m in [UUID.search(f)] if m}
    if not uuids:
        return []
    index = uuid_index(project)
    assets = {index[u] for u in uuids if u in index}
    owned = {u for u, a in index.items() if a in assets} | uuids
    pages, loads = [], []
    # a picture under resources/ can also be loaded by path from code (cc.resources.load('art/buttons/play'))
    keys = set()
    for asset in assets:
        parts = asset.split('/')
        if 'resources' in parts[:-1]:
            keys.add('/'.join(parts[parts.index('resources') + 1:]).rsplit('.', 1)[0])
    root = Path(project) / 'assets'
    for path in sorted(root.rglob('*')) if root.is_dir() else []:
        if not path.is_file() or path.suffix not in ('.prefab', '.fire', '.scene', '.ts', '.js'):
            continue
        try:
            text = path.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        rel = path.relative_to(project).as_posix()
        if path.suffix in ('.ts', '.js'):
            if keys and any("'%s'" % k in text or '"%s"' % k in text for k in keys):
                loads.append(rel + '（代码按路径加载）')
        elif any(u in text for u in owned):
            pages.append(rel)
    return pages + loads


def write_record(project, p, pages):
    folder = Path(project) / 'docs' / 'checks'
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    path = folder / ('rework-%s.json' % stamp)
    n = 2
    while path.exists():
        path = folder / ('rework-%s-%d.json' % (stamp, n))
        n += 1
    todo, skip = ai_checks(p)
    doc = dict(public(p), time=datetime.now().astimezone().isoformat(timespec='seconds'), pages=pages,
               ai={'todo': todo, 'skip': skip}, lines=describe(p, pages))
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return path


def native_files(folder):
    """{name: bytes} of a build folder as the writers zip it (Finder/Windows junk left out like make_tiktok_zip does;
    symlinks, which the writers refuse, skipped)."""
    import verify_native_zip as vnz
    folder = Path(folder)
    out = {}
    for path in sorted(folder.rglob('*')):
        if not path.is_file() or path.is_symlink():
            continue
        name = path.relative_to(folder).as_posix()
        if vnz.forbidden(name) == 'Finder/Windows junk file':
            continue
        out[name] = path.read_bytes()
    return out


def source_settings(project, board=None):
    """-> (board, finalize options) the writers will use: board as given, else the source record's
    (<project>/.tiktok-kit/finalize-source.json, written by `tiktok_finalize.py source --board`), else the project
    marker's; options = the source record's (the writers must pass the same ones, K5)."""
    import tiktok_finalize as F
    from tiktok_finalize_steps import policy as P
    record = F.read_source_record(project) if project else None
    record = record if isinstance(record, dict) else {}
    board = board or record.get('board') or (P.read_marker(project) or {}).get('board')
    options = {k: v for k, v in F.recorded_options(record.get('options')).items() if v}
    return board, options


def app_id_of(zip_path):
    """The App ID in a package's project.config.json (what the last writer's --app-id was), or None."""
    try:
        with zipfile.ZipFile(zip_path) as z:
            doc = json.loads(z.read('project.config.json').decode('utf-8-sig'))
    except (OSError, KeyError, ValueError, zipfile.BadZipFile):
        return None
    value = doc.get('appid') if isinstance(doc, dict) else None
    return str(value) if value else None


def finalized_files(native, project, board=None, app_id=None):
    """-> ({name: bytes}, board): the build `native` as the writers will zip it. Both writers run
    tiktok_finalize.finalize_native on the build folder first (make_tiktok_zip.finalize_for_writer); on a raw Creator
    build that rewrites adapter-min.js and the engine, adds the kit files and recompresses most PNGs (割草小能手 2.4.15:
    3 code files and 66 PNGs), which would read as a code change. The same step runs here on a temporary copy, so the
    build folder is not touched; a second run on a finalized build changes nothing. ValueError when finalize refuses
    (the writer will refuse too)."""
    import shutil
    import tempfile
    import tiktok_finalize as F
    native = Path(native).resolve()
    board, options = source_settings(project, board)
    tmp = Path(tempfile.mkdtemp(prefix='rework-preview-'))
    try:
        copy = tmp / (native.name or 'native')
        shutil.copytree(native, copy, symlinks=True)
        record = F.finalize_native(copy, project, board, app_id, options=options)
        if record.get('blocks'):
            raise ValueError('tiktok_finalize refused a copy of the build (the writer will refuse too): %s' % '; '.join(
                '%s: %s' % (b.get('id'), b.get('message')) for b in record['blocks'][:3]))
        return native_files(copy), board
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def record_for_writer(project, p):
    """Both writers, after the ZIP is published: the plan they used, the pages that use the change and the AI's hand
    checks, written to <project>/docs/checks/rework-<time>.json, so the next AI knows what was checked and what changed.
    Only when an earlier package was compared (none for a first package). Never raises: the ZIP is already published.
    -> {'path', 'pages'} | {'error'} | None"""
    if not project or not isinstance(p, dict) or not p.get('old'):
        return None
    try:
        pages = affected_pages(project, p)
        return {'path': str(write_record(project, p, pages)), 'pages': pages}
    except Exception as error:  # noqa: BLE001 - a missing record never touches the published package
        return {'error': '%s: %s' % (type(error).__name__, error)}


def writer_lines(p, rec=None):
    """The writer's 返工范围 lines: the plan, the pages from its record, and where the record is."""
    pages = rec.get('pages') if isinstance(rec, dict) else None
    lines = describe(p, pages)
    if isinstance(rec, dict):
        lines.append('（返工记录没写成：%s；包已经出好，不受影响）' % rec['error'] if rec.get('error')
                     else '（返工记录：%s）' % rec.get('path'))
    return lines


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            '返工'.encode(stream.encoding or 'ascii')
        except (LookupError, UnicodeEncodeError):
            try:
                stream.reconfigure(encoding='utf-8', errors='replace')
            except (AttributeError, ValueError):
                pass
    ap = argparse.ArgumentParser(prog='rework_scope.py', description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--old', required=True, help='上一个交付包 ZIP，或写着最新.txt 的出包文件夹')
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--native', type=Path, help='这次的 Native 构建目录（还没出包时用，要带 --project）')
    group.add_argument('--new', type=Path, help='这次的包 ZIP')
    ap.add_argument('--project', type=Path, help='游戏工程：列出用到改动的页面，计划记进 docs/checks/')
    ap.add_argument('--app-id', help='目标 App ID（默认用上一个交付包 project.config.json 里的）')
    ap.add_argument('--ad-regression', type=Path, help='适配文件（默认 $TIKTOK_AD_REGRESSION_ADAPTER）')
    ap.add_argument('--board', choices=['localize', 'remake'], help='默认用工程 source 记录里的')
    ap.add_argument('--policy', choices=['new', 'legacy'])
    ap.add_argument('--json', action='store_true', help='打印整份计划 JSON')
    a = ap.parse_args(argv)
    if a.native and not a.project:
        print('rework_scope.py：--native 要带 --project（写包入口出包前会先在构建上装平台件、压 PNG，预览要在构建的副本上做同样'
              '一步，才和写包入口比得一样）', file=sys.stderr)
        return 2
    old, note = resolve(a.old)
    if old is None:
        print('rework_scope.py：' + note, file=sys.stderr)
        return 2
    board = a.board
    try:
        if a.native:
            if not a.native.is_dir():
                raise ValueError('--native %s is not a folder' % a.native)
            new_files, board = finalized_files(a.native, a.project, a.board, a.app_id or app_id_of(old))
        else:
            new_files = read_zip(a.new)
            if a.project:
                board = source_settings(a.project, a.board)[0]
    except Exception as error:  # noqa: BLE001 - kit, copy or finalize problems: no plan, say why
        print('rework_scope.py：%s' % error, file=sys.stderr)
        return 2
    started = time.monotonic()
    p = plan(old, new_files, a.ad_regression, a.policy, board)
    p['plan_seconds'] = round(time.monotonic() - started, 2)
    p['preview'] = 'native, finalized on a copy' if a.native else 'zip'
    pages = affected_pages(a.project, p) if a.project else []
    if a.json:
        print(json.dumps(dict(public(p), pages=pages), ensure_ascii=False, indent=2))
    else:
        print('\n'.join(describe(p, pages)))
        if a.native:
            print('（预览：先在构建的副本上装了平台件、压了 PNG，和写包入口一样；构建文件夹没动。出包时写包入口自己再比一次，以它为准）')
    if a.project:
        print('（记录写进了 %s）' % write_record(a.project, p, pages))
    return 0


if __name__ == '__main__':
    sys.exit(main())
