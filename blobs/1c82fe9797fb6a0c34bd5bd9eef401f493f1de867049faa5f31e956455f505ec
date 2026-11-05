#!/usr/bin/env python3
"""Home-page resource list docs/startup/first-screen.json + size ledger docs/startup/budget.json (生成时预防 P04).

Run it when work starts (new game: right after the project is made; English game: on the original project, before
any change) and after a scene or a bundle is added. Static, a few seconds, no build. The AI runs it; the user never
runs commands.

  python3 -B first_screen.py --project <cocos project> [--board new|localize] [--boot-scene NAME] [--home-scene NAME]
                             [--check] [--json]

Why: the census found first downloads that were too big or stuck (39 + 34 games): the home page asked for the
resources, hallScene and gameScene subpackages before it showed (美女快跑 15.7 MiB), BGM was downloaded on the
loading page (香肠太难了), 61 abandoned scenes stayed in the main package (喂小动物). These were only seen when the
package was written. Here they are found when work starts:
  1. the boot scene (settings builder.json startScene, else --boot-scene, else a loading/launch scene) and the home
     scene (--home-scene, else the first cc.director.loadScene('<name>') in the boot scene's scripts) are read;
     home_needs = what those scenes reference directly (pictures, fonts, prefabs and what the prefabs reference),
     their component scripts and every script those require (parse_package_requires.cjs, called as is), and what
     those scripts load by path (scan_runtime_resources.cjs, called as is; platform-kit parts are not scanned:
     AudioService loads sound after the first frame by itself). Every other file is "deferred".
  2. subpackages requested before the home page (loadBundle / loadSubpackage / bundle.load in those scripts) are
     downloaded whole before the home page shows. One that holds nothing the home page needs is an error (new
     game) / warning (English game): load it after the home page with ResLoader.
  3. a sound loaded by those scripts (cc.AudioClip, an audio file, or a bgm/music/sound path) is an error for a new
     game (warning for an English game): play sound through AudioService, which loads it after the first frame.
  4. a scene outside bundles that no script loads by name and that is not in docs/startup/build-scenes.json
     (make_level_plan.py --project writes it) is built into the main package anyway: error for a new game,
     warning for an English game. Scenes in settings/builder.json excludeScenes are not built and not counted.
  5. the first download (main package + subpackages requested before the home page + engine allowance + bytedance
     template, audit_package_estimate.py's numbers) over 10 MiB is an error on both boards.
The template remake-core/assets/startup-plan-template.json is copied into first-screen.json (timing profiles for
audit_startup_loading.py) with home_assets_allowed filled from home_needs. budget.json is rebuilt from the same
analysis; import_audio.py and the art step add each new file to it (startup_budget.record).
Exit: 0 ok, 1 problems (or --check and the files on disk are stale), 2 bad input. No machine paths.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import audit_package_estimate as estimate  # noqa: E402
import startup_budget  # noqa: E402

SCHEMA = 'first_screen.v1'
OUT = ('docs', 'startup', 'first-screen.json')
WHITELIST = ('docs', 'startup', 'build-scenes.json')
TEMPLATE = HERE.parent / 'assets' / 'startup-plan-template.json'
SCENE_EXT = ('.fire', '.scene')
SCRIPT_EXT = ('.js', '.ts')
IMAGE_EXT = ('.png', '.jpg', '.jpeg', '.webp')
FONT_EXT = ('.ttf', '.otf', '.fnt', '.labelatlas')
AUDIO_EXT = startup_budget.AUDIO
KIT_DIRS = {'tiktok-platform', 'platform-kit', 'generated'}
BOOT_WORDS = ('loading', 'load', 'launch', 'boot', 'splash', 'init', 'start')
HOME_WORDS = ('home', 'main', 'hall', 'menu', 'lobby', 'start', 'index', 'title')
SOUND_PATH = re.compile(r'(^|[/_\-])(bgm|music|sound|sounds|audio|sfx|bg_music)([/_\-.]|$)', re.I)
LOAD_SCENE = re.compile(r'\b(?:loadScene|preloadScene)\s*\(\s*["\']([^"\']+)["\']')
LOAD_BUNDLE = re.compile(r'loadSubpackage\s*\(\s*\{[^}]{0,300}?\bname\s*:\s*["\']([^"\']+)["\']|'
                         r'loadSubpackage\s*\(\s*["\']([^"\']+)["\']|loadBundle\s*\(\s*["\']([^"\']+)["\']')
REQUIRE = re.compile(r'\brequire\s*\(\s*["\']([^"\']+)["\']\s*\)|\bimport\s[^;]*?from\s*["\']([^"\']+)["\']')
RAW_LOAD = re.compile(r'\b(?:cc\.resources\.load|resources\.load|cc\.loader\.loadRes)\s*\(\s*["\']([^"\']+)["\']'
                      r'(?:\s*,\s*(cc\.\w+))?')
B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
METHOD = re.compile(r'\b([A-Za-z_$][\w$]*)\s*:\s*function\b|^[ \t]*(?:(?:public|private|protected|static|async)\s+)*'
                    r'([A-Za-z_$][\w$]*)\s*\([^()]*\)\s*(?::\s*[\w<>\[\]|]+\s*)?\{', re.M)
KEYWORDS = {'function', 'if', 'for', 'while', 'switch', 'catch', 'with', 'return', 'else'}
LIFECYCLE = {'onLoad', 'start', 'onEnable', '__preload', 'ctor', 'constructor', 'init'}


def enclosing_method(text: str, offset: int) -> str | None:
    """Name of the nearest method defined before offset (cc.Class 'name: function' or a class method); None at top level."""
    name = None
    for m in METHOD.finditer(text, 0, offset):
        n = m.group(1) or m.group(2)
        if n not in KEYWORDS:
            name = n
    return name


def runs_before_home(text: str, offset: int, loading_page: bool) -> bool:
    """Everything on the loading page runs before the home page; on the home page only start-up methods do (a PLAY
    handler that loads the level bundle is after the first frame)."""
    return loading_page or enclosing_method(text, offset) in LIFECYCLE | {None}


def decompress_uuid(s: str) -> str | None:
    """Cocos class id of a script component (22/23 chars) -> the script's .meta uuid."""
    if len(s) == 23:
        head, rest = s[:5], s[5:]
    elif len(s) == 22:
        head, rest = s[:2], s[2:]
    else:
        return None
    try:
        out = head
        for i in range(0, len(rest), 2):
            a, b = B64.index(rest[i]), B64.index(rest[i + 1])
            out += '%x%x%x' % (a >> 2, ((a & 3) << 2) | (b >> 4), b & 15)
    except (ValueError, IndexError):
        return None
    if len(out) != 32:
        return None
    return '%s-%s-%s-%s-%s' % (out[:8], out[8:12], out[12:16], out[16:20], out[20:])


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError, UnicodeDecodeError):
        return None


class Project:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.assets = self.root / 'assets'
        self.files = [p for p in estimate.files(self.assets) if p.suffix != '.meta']
        self.rel = {p: p.relative_to(self.root).as_posix() for p in self.files}
        self.by_uuid = {}
        for p in self.files:
            for u in estimate.asset_uuids(p):
                self.by_uuid.setdefault(u, p)
        self.bundles = estimate.bundles(self.root)          # 'folder' (under assets/) -> bytedance compression type
        self.sub = sorted(b for b, t in self.bundles.items() if t == 'subpackage')
        self.names = {}                                      # bundle name used in code -> folder
        for folder in self.bundles:
            meta = read_json(self.assets / (folder + '.meta')) or {}
            user = meta.get('userData') if isinstance(meta.get('userData'), dict) else {}
            self.names[meta.get('bundleName') or user.get('bundleName') or folder.split('/')[-1]] = folder
        self.names.setdefault('resources', 'resources')
        self.scenes = [p for p in self.files if p.suffix in SCENE_EXT]
        self.scripts = [p for p in self.files if p.suffix in SCRIPT_EXT and not p.name.endswith('.d.ts')]
        self.by_stem = {}
        for p in self.scripts:
            self.by_stem.setdefault(p.stem, p)

    def bundle_of(self, path: Path) -> str | None:
        rel = path.relative_to(self.assets).as_posix()
        owner = None
        for b in self.bundles:
            if (rel == b or rel.startswith(b + '/')) and (owner is None or len(b) > len(owner)):
                owner = b
        return owner

    def scene_named(self, name: str):
        for p in self.scenes:
            if p.stem == name or p.stem.lower() == name.lower():
                return p
        return None


def refs_of(path: Path) -> set:
    try:
        text = path.read_text(encoding='utf-8', errors='ignore')
    except OSError:
        return set()
    return {m.split('@')[0] for m in estimate.UUID_REF.findall(text)}


def script_uuids(path: Path) -> set:
    data = read_json(path)
    out = set()
    if isinstance(data, list):
        for o in data:
            t = o.get('__type__') if isinstance(o, dict) else None
            if isinstance(t, str) and not t.startswith(('cc.', 'sp.', 'dragonBones.')):
                u = decompress_uuid(t)
                if u:
                    out.add(u)
    return out


def node_bin() -> str | None:
    return shutil.which('node') or shutil.which('nodejs')


def requires_of(path: Path, node: str | None) -> list:
    text = path.read_text(encoding='utf-8', errors='ignore')
    if node and path.suffix == '.js':
        run = subprocess.run([node, str(HERE / 'parse_package_requires.cjs')], input=text, capture_output=True,
                             text=True, timeout=30)
        try:
            data = json.loads(run.stdout or '{}')
        except ValueError:
            data = {}
        if 'dependencies' in data:
            return [d['request'] for d in data['dependencies']]
    return [a or b for a, b in REQUIRE.findall(text)]


def resource_sites(scripts: dict, node: str | None) -> list:
    """{rel: text} -> [{source, bundles, paths, type}] from scan_runtime_resources.cjs (regex if node is missing)."""
    js = {k: v for k, v in scripts.items() if k.endswith('.js')}
    sites = []
    if node and js:
        run = subprocess.run([node, str(HERE / 'scan_runtime_resources.cjs')], input=json.dumps({'files': js}),
                             capture_output=True, text=True, timeout=30)
        try:
            data = json.loads(run.stdout or '{}')
        except ValueError:
            data = {}
        if 'sites' in data:
            sites = [{'source': s['source'], 'bundles': s.get('bundles') or [], 'paths': s.get('paths') or [],
                      'type': s.get('type'), 'line': s.get('line'),
                      'offset': int(str(s.get('id', '')).rsplit(':', 1)[-1] or 0) if str(s.get('id', '')).rsplit(':', 1)[-1].isdigit() else 0}
                     for s in data['sites']]
            js = {}
    for rel, text in list(js.items()) + [(k, v) for k, v in scripts.items() if not k.endswith('.js')]:
        for m in RAW_LOAD.finditer(text):
            sites.append({'source': rel, 'bundles': ['resources'], 'paths': [m.group(1)], 'type': m.group(2),
                          'line': text.count('\n', 0, m.start()) + 1, 'offset': m.start()})
    return sites


def start_scene(pr: Project, boot_name: str | None):
    if boot_name:
        return pr.scene_named(boot_name)
    for cfg in (pr.root / 'settings' / 'builder.json', pr.root / 'settings' / 'v2' / 'packages' / 'builder.json'):
        data = read_json(cfg) or {}
        u = data.get('startScene')
        if isinstance(u, str) and u in pr.by_uuid:
            return pr.by_uuid[u]
    if len(pr.scenes) == 1:
        return pr.scenes[0]
    for words in (BOOT_WORDS, HOME_WORDS):
        for w in words:
            for p in pr.scenes:
                if p.stem.lower() == w or p.stem.lower().startswith(w):
                    return p
    return None


def excluded_scenes(pr: Project) -> set:
    out = set()
    for cfg in (pr.root / 'settings' / 'builder.json',):
        data = read_json(cfg) or {}
        for u in data.get('excludeScenes') or []:
            if u in pr.by_uuid:
                out.add(pr.by_uuid[u])
    return out


def analyze(project, board: str = 'new', boot_name: str | None = None, home_name: str | None = None) -> dict:
    project = Path(project)
    if not (project / 'assets').is_dir():
        raise ValueError('not a Cocos project (no assets folder): %s' % project)
    pr = Project(project)
    node = node_bin()
    strict = board != 'localize'
    problems, warnings = [], []
    boot = start_scene(pr, boot_name)
    if boot is None:
        raise ValueError('cannot tell the start scene: pass --boot-scene NAME')
    script_uuid = {u: p for p in pr.scripts for u in estimate.asset_uuids(p)}

    def closure(scenes):
        assets, scripts, todo, seen = set(), set(), list(scenes), set()
        while todo:
            f = todo.pop()
            if f in seen:
                continue
            seen.add(f)
            assets.add(f)
            for u in script_uuids(f):
                if u in script_uuid:
                    scripts.add(script_uuid[u])
            for u in refs_of(f):
                p = pr.by_uuid.get(u)
                if p is None or p.suffix in SCENE_EXT:
                    continue
                if p.suffix in ('.prefab', '.anim', '.mtl', '.labelatlas', '.plist'):
                    todo.append(p)
                else:
                    assets.add(p)
        todo = list(scripts)
        while todo:
            s = todo.pop()
            for req in requires_of(s, node):
                p = None if req in ('cc', 'tt') else pr.by_stem.get(Path(req).stem)
                if p is not None and p not in scripts:
                    scripts.add(p)
                    todo.append(p)
        return assets, scripts

    boot_assets, boot_scripts = closure([boot])
    texts = {pr.rel[s]: s.read_text(encoding='utf-8', errors='ignore') for s in boot_scripts}
    home = pr.scene_named(home_name) if home_name else None
    if home is None and not home_name:
        for text in texts.values():
            m = LOAD_SCENE.search(text)
            if m and pr.scene_named(m.group(1)):
                home = pr.scene_named(m.group(1))
                break
    home = home or boot
    home_assets, home_scripts = closure([home]) if home != boot else (set(), set())
    assets = boot_assets | home_assets
    scripts = boot_scripts | home_scripts
    for s in home_scripts:
        texts.setdefault(pr.rel[s], s.read_text(encoding='utf-8', errors='ignore'))
    scan = {k: v for k, v in texts.items() if not KIT_DIRS & set(Path(k).parts[:-1])}
    sites = resource_sites(scan, node)
    loaded, requested, sound = set(), {}, []
    boot_rel = {pr.rel[s] for s in boot_scripts} if home != boot else set()
    for rel, text in scan.items():
        for m in LOAD_BUNDLE.finditer(text):
            if runs_before_home(text, m.start(), rel in boot_rel):
                name = next(x for x in m.groups() if x)
                requested.setdefault(pr.names.get(name, name), '%s:%d' % (rel, text.count('\n', 0, m.start()) + 1))
    for site in sites:
        if not runs_before_home(scan.get(site['source'], ''), site.get('offset', 0), site['source'] in boot_rel):
            continue
        for b in site['bundles']:
            folder = pr.names.get(b, b)
            requested.setdefault(folder, '%s:%s' % (site['source'], site['line']))
            for path in site['paths']:
                path = re.sub(r'/(spriteFrame|texture)$', '', path)
                hits = [p for p in pr.files if pr.bundle_of(p) == folder and p.suffix != '.meta' and
                        (pr.assets / folder / path).as_posix() == p.with_suffix('').as_posix()]
                loaded.update(hits)
                is_sound = (site.get('type') or '').endswith('AudioClip') or any(h.suffix.lower() in AUDIO_EXT for h in hits) \
                    or SOUND_PATH.search('/' + path)
                if is_sound:
                    sound.append('%s:%s loads %s/%s' % (site['source'], site['line'], b, path))
    for s in sound:
        (problems if strict else warnings).append(
            'audio_before_first_frame: %s before the home page shows; play sound through AudioService (it loads '
            'after the first frame), never from the loading/home script' % s)
    home_set = assets | scripts | loaded | {boot, home}
    # scenes that go into the build
    excluded = excluded_scenes(pr)
    wl = read_json(project.joinpath(*WHITELIST)) or {}
    whitelist = set(wl.get('scenes') or []) if isinstance(wl, dict) else set()
    by_name = set()
    for s in pr.scripts:
        by_name.update(LOAD_SCENE.findall(s.read_text(encoding='utf-8', errors='ignore')))
    unused = []
    for sc in pr.scenes:
        if sc in (boot, home) or sc in excluded or pr.bundle_of(sc) is not None:
            continue
        if sc.stem in by_name or sc.stem in whitelist:
            continue
        unused.append(sc)
    if unused:
        names = ', '.join(sorted(s.stem for s in unused)[:12])
        (problems if strict else warnings).append(
            'unused_scene_in_main: %d scene(s) no script loads and not in docs/startup/build-scenes.json are built into '
            'the main package (%s%s): run make_level_plan.py --project (writes the whitelist and builder.json '
            'excludeScenes) or delete them' % (len(unused), names, ' ...' if len(unused) > 12 else ''))
    built_scenes = [s for s in pr.scenes if s not in excluded]
    refs = set()
    for f in pr.files:
        if f.suffix in SCENE_EXT and f in excluded:
            continue
        if f.suffix in SCENE_EXT + ('.prefab', '.anim', '.mtl', '.json', '.pmtl', '.effect', '.labelatlas', '.plist'):
            refs |= refs_of(f)
    # first download: main package + subpackages requested before the home page
    early_sub = sorted(b for b in requested if b in pr.sub)
    rows, home_rows, deferred = {}, [], []
    for f in pr.files:
        if f.suffix in SCENE_EXT and f in excluded:
            continue
        b = pr.bundle_of(f)
        if b is None and f.suffix not in SCENE_EXT + SCRIPT_EXT and not estimate.asset_uuids(f) & refs:
            continue                                        # outside bundles and unreferenced: not built
        first = b not in pr.sub or b in early_sub
        need = 'home' if f in home_set else 'deferred'
        size = startup_budget.counted_bytes(f)
        row = {'file': pr.rel[f], 'bytes': size, 'bundle': b or 'main'}
        if need == 'home':
            home_rows.append(row)
        else:
            deferred.append(dict(row, in_first_download=first))
        if first:
            rows[pr.rel[f]] = {'bytes': size, 'need': need, 'first_download': True, 'source': 'first_screen'}
    for b in early_sub:
        if not any(r['bundle'] == b for r in home_rows):
            (problems if strict else warnings).append(
                'prehome_bundle_not_home: subpackage %s (%.2f MiB) is requested before the home page (%s) but the home '
                'page uses nothing in it: load it after the home page with ResLoader' % (
                    b, sum(r['bytes'] for r in deferred if r['bundle'] == b) / 1048576.0, requested[b]))
    groups = {'subpackage_bundles': pr.sub, 'main_bundles': sorted(b for b in pr.bundles if b not in pr.sub),
              'pre_home_bundles': early_sub}
    ledger = startup_budget.new_ledger(project, rows, groups)
    summary = startup_budget.summarize(ledger)
    if summary['over']:
        problems.append('first_download_over_limit: %.2f MiB > %.0f MiB before the home page (main package %s): move '
                        'deferred files into a subpackage bundle loaded after the home page' % (
                            summary['first_download_bytes'] / 1048576.0, summary['limit_bytes'] / 1048576.0,
                            '+ ' + ', '.join(early_sub) if early_sub else 'only'))
    deferred_main = sum(r['bytes'] for r in deferred if r['in_first_download'])
    if deferred_main > 1048576:
        warnings.append('deferred_in_first_download: %.2f MiB the home page does not use is in the first download; '
                        'move it into a subpackage bundle' % (deferred_main / 1048576.0))
    plan = read_json(TEMPLATE) or {}
    plan = {k: v for k, v in plan.items() if k not in ('binding', 'run_plan_example')}
    max_kb = plan.get('max_home_asset_kb', 500)
    plan['home_assets_allowed'] = sorted(Path(r['file']).stem for r in home_rows
                                         if r['file'].lower().endswith(IMAGE_EXT + FONT_EXT))
    for r in home_rows:
        if r['file'].lower().endswith(IMAGE_EXT) and r['bytes'] > max_kb * 1024:
            warnings.append('home_image_large: %s is %d KB > max_home_asset_kb %d' % (r['file'], r['bytes'] // 1024, max_kb))
    kind = lambda r: ('scene' if r['file'].endswith(SCENE_EXT) else 'script' if r['file'].endswith(SCRIPT_EXT) else
                      'image' if r['file'].lower().endswith(IMAGE_EXT) else 'font' if r['file'].lower().endswith(FONT_EXT)
                      else 'audio' if r['file'].lower().endswith(AUDIO_EXT) else 'other')
    report = {'schema': SCHEMA, 'tool': 'first_screen', 'board': board,
              'template': 'remake-core/assets/startup-plan-template.json', **plan,
              'boot_scene': pr.rel[boot], 'home_scene': pr.rel[home],
              'home_needs': {'files': sorted((dict(r, kind=kind(r)) for r in home_rows), key=lambda r: r['file'])},
              'deferred': sorted(deferred, key=lambda r: r['file']),
              'pre_home_bundles': {b: requested[b] for b in early_sub}, 'groups': groups,
              'build_scenes': sorted(pr.rel[s] for s in built_scenes if s not in unused),
              'unused_scenes': sorted(pr.rel[s] for s in unused),
              'estimate': summary, 'problems': problems, 'warnings': warnings, 'ok': not problems,
              'parsers': 'parse_package_requires.cjs + scan_runtime_resources.cjs' if node else 'regex (node not found)',
              '_ledger': ledger}
    return report


def render(report: dict) -> tuple[str, str]:
    r = dict(report)
    ledger = r.pop('_ledger')
    return (json.dumps(r, ensure_ascii=False, indent=1) + '\n',
            json.dumps(dict(ledger, summary=startup_budget.summarize(ledger)), ensure_ascii=False, indent=1) + '\n')


def write(project, report: dict) -> None:
    project = Path(project)
    fs, _ = render(report)
    out = project.joinpath(*OUT)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(fs, encoding='utf-8')
    old = startup_budget.ledger_path(project)
    ledger = dict(report['_ledger'])
    if old.is_file():                                       # keep rows other steps added for files not seen here
        prev = read_json(old) or {}
        for f, row in (prev.get('files') or {}).items():
            if f not in ledger['files'] and row.get('source') != 'first_screen' and (project / f).is_file():
                ledger['files'][f] = row
    startup_budget.save(project, ledger)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--board', choices=('new', 'localize'), default=None,
                    help='new = new/remake game (problems are errors); localize = English game (only the size limit '
                         'is an error). Default: docs/board.txt, else new')
    ap.add_argument('--boot-scene')
    ap.add_argument('--home-scene')
    ap.add_argument('--check', action='store_true', help='write nothing; exit 1 when first-screen.json is stale')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    board = a.board
    if board is None:
        bt = a.project / 'docs' / 'board.txt'
        board = 'localize' if bt.is_file() and 'localize' in bt.read_text(encoding='utf-8', errors='ignore') else 'new'
    try:
        report = analyze(a.project, board, a.boot_scene, a.home_scene)
    except ValueError as exc:
        print(json.dumps({'status': 'error', 'error': str(exc)}, ensure_ascii=False))
        return 2
    stale = False
    if a.check:
        out = a.project.joinpath(*OUT)
        stale = not out.is_file() or render(report)[0] != out.read_text(encoding='utf-8')
    else:
        write(a.project, report)
    brief = {k: report[k] for k in ('ok', 'board', 'boot_scene', 'home_scene', 'pre_home_bundles', 'problems', 'warnings')}
    brief.update(home_needs=len(report['home_needs']['files']), deferred=len(report['deferred']),
                 first_download_mib=round(report['estimate']['first_download_bytes'] / 1048576.0, 2), stale=stale)
    print(json.dumps(report if a.json else brief, ensure_ascii=False, default=str))
    return 1 if report['problems'] or stale else 0


if __name__ == '__main__':
    sys.exit(main())
