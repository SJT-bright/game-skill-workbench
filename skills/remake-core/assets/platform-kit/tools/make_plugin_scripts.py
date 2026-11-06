#!/usr/bin/env python3
"""Generate the Cocos 3.x platform-kit plugin scripts and KIT_PARTS_3X.json (kit 2.0, design D77 1.5 / 3.3, W-A2).

    python3 tools/make_plugin_scripts.py           # write plugins-3x/*.plugin.js and parts-3x/KIT_PARTS_3X.json
    python3 tools/make_plugin_scripts.py --check   # write nothing; exit 1 when any generated file is stale

Each plugins-3x/<Name>.plugin.js wraps assets/tiktok-platform/<Name>.js (the 2.4 module) byte for byte between a
BEGIN and an END line. Cocos 3.x runs a plugin script as a plain global script (no require/module), so the wrapper
gives the module its own `module`/`exports` and a `require('./X')` that returns globalThis.TikTokKit.X, and
publishes the module as globalThis.TikTokKit.<Name>. Each module runs on first use, so the load order of the
plugin scripts does not matter. The kit hash of every generated file is written into parts-3x/KIT_PARTS_3X.json,
which KIT_MANIFEST.json pulls in through "includes"; nothing else carries these hashes.

--check proves three things and names every failure:
  1. the code between BEGIN and END of each plugin equals its 2.4 module byte for byte;
  2. each plugin file equals what this script generates from the current 2.4 module (wrapper unchanged);
  3. KIT_PARTS_3X.json equals what this script generates (hashes of the plugins, tiktok-touch-3x.js,
     parts/storage-guard.js, parts/host-shim.js and parts-3x/boot-guard-3x.js are current).
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
KIT_VERSION = '2.0'
SRC_DIR = 'assets/tiktok-platform'
OUT_DIR = 'plugins-3x'
PARTS_FILE = 'parts-3x/KIT_PARTS_3X.json'
# (module, part name, editable). HomeGrowthEntries.js is a Cocos 2.4 cc.Class component: not a 3.x plugin.
MODULES = [
    ('PlatformConfig', 'platformconfig3x', True),
    ('TikTokMissionService', 'missions3x', False),
    ('RewardedService', 'rewarded3x', False),
    ('SaveStore', 'savestore3x', False),
    ('MissionFlow', 'missionflow3x', False),
    ('HomeEntrySlots', 'homeslots3x', False),   # 生成时预防 R4G1: 3.x home entries find their free place at runtime
]
# 生成时预防 R4G1: modules whose 2.4-side source is not in assets/tiktok-platform (parts/ = not a 2.4 kit project file).
MODULE_SRC = {'HomeEntrySlots': 'parts'}
# R4G1: parts/HomeEntrySlots.js carries the slot code of HomeGrowthEntries.js byte for byte between these lines.
SLOTS_SRC, SLOTS_FROM = 'parts/HomeEntrySlots.js', 'assets/tiktok-platform/HomeGrowthEntries.js'
SLOTS_BEGIN = '// ---- BEGIN slot code of assets/tiktok-platform/HomeGrowthEntries.js ----\n'
SLOTS_END = '// ---- END slot code of assets/tiktok-platform/HomeGrowthEntries.js ----\n'
SLOTS_CUT = ('// ------------------------------------------------------------- free place for the entries',
             'Controller.findFreeSlots = findFreeSlots;\n')


def src_of(name):
    return '%s/%s.js' % (MODULE_SRC.get(name, SRC_DIR), name)


def slots_problems():
    """R4G1: [problem] when parts/HomeEntrySlots.js no longer has HomeGrowthEntries.js's slot code byte for byte."""
    try:
        own, hge = read(SLOTS_SRC).decode('utf-8'), read(SLOTS_FROM).decode('utf-8')
    except (OSError, UnicodeDecodeError) as error:
        return ['cannot read the home slot code: %s' % error]
    a, b = hge.find(SLOTS_CUT[0]), hge.find(SLOTS_CUT[1])
    if a < 0 or b < a:
        return ['%s: slot code anchors missing (free place / Controller.findFreeSlots)' % SLOTS_FROM]
    if own.count(SLOTS_BEGIN) != 1 or own.count(SLOTS_END) != 1:
        return ['%s: BEGIN/END slot code lines missing or repeated' % SLOTS_SRC]
    core = own[own.index(SLOTS_BEGIN) + len(SLOTS_BEGIN):own.index(SLOTS_END)]
    if core != hge[a:b]:
        return ['%s: slot code differs from %s (copy it again byte for byte; same search on 2.4 and 3.x)'
                % (SLOTS_SRC, SLOTS_FROM)]
    return []
# Hashes of earlier kit releases of each generated or placed file (kit_old).
# v7.7.4: MissionFlow's preview text 'LOCAL PREVIEW: ...' -> 'Available in TikTok.' (audit_dev_text refused it).
# v7.9 (手机问题源头约束): tiktok-touch-3x.js 7027f538 = kit 2.0 until v7.9 (coordinates only); the current file also
# gives the engine a touchcancel for touches still down on tt.onHide / tt.onShow (猴子快跑 v12).
# D2 (2026-11-04): RewardedService.plugin.js 16880d5b = 简化.11.5～11.12 (RewardedService 7a446726, no pass-through
# mark for parts/rewarded-guard.js).
# 简化.11.13 P10 (I1): SaveStore.plugin.js c6d7b35f = the plugin of the SaveStore.js before grant() / best().
# R4E: dcf16d37 = the plugin of SaveStore.js 9fca45e2 (简化.11.13, before the read-time schema check).
# R4J1: 81f90088 = the plugin of SaveStore.js ba99f771 (R4E, before schema 2 and the dated grant id clean-up).
PREVIOUS = {'missionflow3x': ['9a7f33e4684f1ff0ce558afeece333036541ff8798f4547748d4793a3d10e2c2'],
            'rewarded3x': ['16880d5ba2e674202dcc9c285c5a228a224b3581a1ff4a369a4fa7b774c5c01a'],
            'savestore3x': ['c6d7b35f87ec51d5c768a33636354506c238bd86f92ab5c5847687499cd31eb1',
                            'dcf16d37f6032f97e799624f2da01ccf972686bc93305cd778f4f0a207f38a59',
                            '81f900888a76c56f72aac1817070cb8446095825c51fdab074f6319a492f39d5',
                            '1076eae52c305e0c666a0e105639b780857954c909676f7f762358b684f601f9'],   # R4N6: before 'wheel:'
            'boot3x': ['bb1a107005af791144137d36894217a538b225eadda801051714f9cb91563dab'],   # R4Q5: before stats off at home
            'touch3x': ['7027f5388161bffe7dcf52231b5b8de27cbfc62e1fb8e519b3b8027788478b86']}
TOUCH_SRC = 'build-templates/bytedance-mini-game/tiktok-touch-3x.js'
STORAGE_SRC = 'parts/storage-guard.js'
WEB_ADAPTER = r"""require\(\s*['"]\./web-adapter(?:\.js)?['"]\s*\)\s*;?"""
SDK_ARG = 'globalThis.TTMinis&&TTMinis.game||globalThis.tt'
# 生成时预防 R4B (问题普查 startup_stuck 34 款, startup_retry_broken 27, host_api_mismatch 12): the host shim and the
# 3.x startup guard become parts that tiktok_finalize installs (step hostshim / boot in tiktok_finalize_steps/startup.py).
HOSTSHIM_SRC = 'parts/host-shim.js'
BOOT_SRC = 'parts-3x/boot-guard-3x.js'
SYSTEM_WARMUP = r"""System\s*\.\s*warmup\s*\("""
BOOT_OWN = [r"""require\(\s*['"]\./boot-loading""", r'native-recovery', r'tiktok-boot3x-own']
# 生成时预防 R4G2 (#29, 问题普查 capsule_overlap 15/15): kit parts/ files wrapped as 3.x plugin scripts the same way.
# They carry "step": "capsule_auto", so kit_sources / K1_plugin3x leave them alone and the source step capsule_auto
# installs them (new 3.x games only; English and legacy games get the top-bar warning). (module, part, eager)
# eager: the plugin loads its module as soon as it runs (CapsuleAuto only listens to scene launches).
PART_PLUGINS = [('CapsuleLayout', 'capsulelayout3x', False), ('CapsuleAuto', 'capsuleauto3x', True)]
PART_SRC_DIR = 'parts'
# 生成时预防 R4G2 (R4A 留下的 3.x guard): parts/rewarded-guard.js (same file and sha as the 2.4 part rewarded24, so
# ads_static.kit_guard_hashes knows it) right AFTER web-adapter.js like storage3x; installed by the startup step.
REWARD_GUARD_SRC = 'parts/rewarded-guard.js'
# 生成时预防 R4N6 (补查2 第 11 组, 合成进化恐龙 55 unresolved-module, 奔跑吧巨人 RewardedService 未注册): the .meta flags
# every 3.x kit plugin script must carry; tiktok_finalize sync writes them (kit_sources.PLUGIN_FLAGS, the same values)
# and checks them at the end of sync (tiktok_finalize_steps/plugin3x_scan.py). Game code uses the parts only through
# globalThis.TikTokKit.<Name> / the Tiktok* globals, never `import ... from '.../RewardedService'`.
PLUGIN_META_FLAGS = {'isPlugin': True, 'loadPluginInWeb': True, 'loadPluginInNative': True, 'loadPluginInMiniGame': True}

HEAD = """\
// tiktok-kit:plugin3x:{name}:{ver}  Cocos 3.x plugin script (import as plugin: native + mini-game). GENERATED by
// tools/make_plugin_scripts.py from {src} (sha256 {sha}). Do not edit
// {edit}
// Publishes globalThis.TikTokKit.{name}. The code between BEGIN and END is the 2.4 module byte for byte;
// require('./X') inside it returns globalThis.TikTokKit.X (another kit plugin script). The module runs on first
// use, so the kit plugin scripts may load in any order.
(function (root) {{
  var kit = root.TikTokKit = root.TikTokKit || {{}};
  var NAME = '{name}', SHA = '{sha}';
  if (Object.getOwnPropertyDescriptor(kit, NAME) && kit['__sha_' + NAME] === SHA) return; // loaded twice: keep the first
  function kitRequire(id) {{
    var key = String(id).replace(/^.*[\\\\/]/, '').replace(/\\.js$/, '');
    if (!Object.prototype.hasOwnProperty.call(kit, key)) {{
      throw new Error('TikTokKit.' + key + ' is not loaded (needed by ' + NAME + '): add ' + key + '.plugin.js');
    }}
    return kit[key];
  }}
  function body(module, exports, require) {{
// ---- BEGIN {src} ----
"""
TAIL = """\
// ---- END {src} ----
  }}
  var state = 0, value;
  function load() {{
    if (state === 2) return value;
    if (state === 1) throw new Error('TikTokKit.' + NAME + ': circular require');
    state = 1;
    var module = {{exports: {{}}}};
    try {{ body.call(module.exports, module, module.exports, kitRequire); }} catch (e) {{ state = 0; throw e; }}
    value = module.exports; state = 2;
    Object.defineProperty(kit, NAME, {{value: value, enumerable: true, configurable: true, writable: false}});
    return value;
  }}
  Object.defineProperty(kit, NAME, {{get: load, enumerable: true, configurable: true}});
  Object.defineProperty(kit, '__sha_' + NAME, {{value: SHA, enumerable: false, configurable: true}});
}})(typeof globalThis !== 'undefined' ? globalThis : typeof GameGlobal !== 'undefined' ? GameGlobal :
  typeof window !== 'undefined' ? window : this);
"""
EDIT_NOTE = {True: "by hand except gameId / appId / placementMap / normalLevelCoins inside BEGIN..END (per game, like 2.4;\n// growthReward() = 5B is fixed, never edited).",
             False: "by hand; regenerate after changing the 2.4 module."}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def begin_line(src):
    return '// ---- BEGIN %s ----\n' % src


def end_line(src):
    return '// ---- END %s ----\n' % src


EAGER_TAIL = """\
// eager (生成时预防 R4G2): {name} only listens, so it starts as soon as this plugin script runs
(function (root) {{ try {{ var k = root.TikTokKit; if (k) void k.{name}; }} catch (e) {{}} }})(
  typeof globalThis !== 'undefined' ? globalThis : typeof GameGlobal !== 'undefined' ? GameGlobal :
  typeof window !== 'undefined' ? window : this);
"""


def render_plugin(name, source, editable, src_dir=None, eager=False):
    src = '%s/%s.js' % (src_dir, name) if src_dir else src_of(name)   # R4G1 src_of + R4G2 src_dir
    text = source.decode('utf-8')
    if not text.endswith('\n'):
        raise ValueError('%s must end with a newline' % src)
    for line in (begin_line(src), end_line(src)):
        if line.strip() in text:
            raise ValueError('%s contains its own BEGIN/END marker line' % src)
    head = HEAD.format(name=name, ver=KIT_VERSION, src=src, sha=sha256(source), edit=EDIT_NOTE[editable])
    return (head + text + TAIL.format(src=src) + (EAGER_TAIL.format(name=name) if eager else '')).encode('utf-8')


def extract_core(name, plugin, src_dir=None):
    """The bytes between BEGIN and END of a plugin file (None when the markers are not there exactly once)."""
    src = '%s/%s.js' % (src_dir, name) if src_dir else src_of(name)
    b, e = begin_line(src).encode('utf-8'), end_line(src).encode('utf-8')
    if plugin.count(b) != 1 or plugin.count(e) != 1:
        return None
    start = plugin.index(b) + len(b)
    end = plugin.index(e)
    return plugin[start:end] if end >= start else None


def read(rel):
    path = KIT / rel
    if not path.is_file():
        raise FileNotFoundError('kit file missing: %s' % rel)
    return path.read_bytes()


def wire(part, line, anchor, after=False):
    key = 'insert_after' if after else 'insert_before'
    return {'in': 'game.js', key: anchor, 'line': '%s // tiktok-kit:%s:%s' % (line, part, KIT_VERSION)}


def render_parts(plugins):
    """KIT_PARTS_3X.json bytes. plugins: {module name: generated plugin bytes}."""
    parts = {}
    for name, part, editable in MODULES:
        dest = '%s/%s.plugin.js' % (SRC_DIR, name)
        parts[part] = {
            'engine': 3, 'phase': 'source', 'plugin': True, 'editable': editable,
            'file': {'src': '%s/%s.plugin.js' % (OUT_DIR, name), 'dest': dest, 'sha256': sha256(plugins[name]),
                     'previous_sha256': PREVIOUS.get(part, []),
                     'from': src_of(name), 'from_sha256': sha256(read(src_of(name)))},
            'global': 'globalThis.TikTokKit.%s' % name,
            'policy': {'new': 'replace', 'legacy': 'report'},
            'note': ('per-game values (gameId / appId / placementMap / normalLevelCoins; growthReward() = 5B is fixed) are '
                     'edited inside BEGIN..END; K1 checks '
                     'presence only' if editable else
                     'byte-identical to the kit; the 2.4 module between BEGIN..END (tools/make_plugin_scripts.py --check)')
                    + '. Checked in the project (source record): a Cocos 3.x build may minify plugin scripts.'}
    for name, part, eager in PART_PLUGINS:   # 生成时预防 R4G2 (#29)
        parts[part] = {
            'engine': 3, 'phase': 'source', 'plugin': True, 'editable': False, 'step': 'capsule_auto',
            'file': {'src': '%s/%s.plugin.js' % (OUT_DIR, name), 'dest': '%s/%s.plugin.js' % (SRC_DIR, name),
                     'sha256': sha256(plugins[name]), 'previous_sha256': PREVIOUS.get(part, []),
                     'from': '%s/%s.js' % (PART_SRC_DIR, name),
                     'from_sha256': sha256(read('%s/%s.js' % (PART_SRC_DIR, name)))},
            'global': 'globalThis.TikTokKit.%s' % name,
            'policy': {'new': 'replace', 'legacy': 'report'},
            'note': 'byte-identical to the kit; %s/%s.js between BEGIN..END%s. Installed by tiktok_finalize source '
                    '(step capsule_auto) for new 3.x games only; English and legacy games: K_W_capsule_auto lists the '
                    'top-bar nodes. Not part of kit_sources / K1_plugin3x. Node-tested (tests/capsule-auto-3x.test.js); '
                    '待真机复测.' % (PART_SRC_DIR, name, ' (eager: starts when the plugin runs)' if eager else '')}
    parts['touch3x'] = {
        'engine': 3, 'phase': 'native',
        'file': {'src': TOUCH_SRC, 'dest': 'tiktok-touch-3x.js', 'template': TOUCH_SRC,
                 'sha256': sha256(read(TOUCH_SRC)), 'previous_sha256': PREVIOUS.get('touch3x', [])},
        'wiring': [wire('touch3x', "require('./tiktok-touch-3x.js').install(%s);" % SDK_ARG, WEB_ADAPTER)],
        'own_markers': [r'marlow-touch', r'grotto-touch', r'tiktok-touch-adapter:', r'__starPopTouchCoordinates',
                        r"""['"]onTouch['"]\s*\+\s*[A-Za-z_$]""",
                        r'\b(?:tt|TTMinis\s*\.\s*game)\s*\.\s*onTouch(?:Start|Move|End|Cancel)\s*=(?!=)',
                        r"""\[\s*['"]onTouch(?:Start|Move|End|Cancel)['"]\s*\]\s*=(?!=)"""],
        'policy': {'new': 'replace', 'legacy': 'add_if_absent'},
        'note': 'before web-adapter.js: the engine clones tt when cc is evaluated. Proof: Marlows R4 '
                'probe_cocos3_touch_coordinates.cjs 1/8 -> 8/8 with this line, back to 1/8 without it.'}
    parts['storage3x'] = {
        'engine': 3, 'phase': 'native',
        'file': {'src': STORAGE_SRC, 'dest': 'storage-guard.js',
                 'template': 'build-templates/bytedance-mini-game/storage-guard.js',
                 'sha256': sha256(read(STORAGE_SRC)), 'previous_sha256': PREVIOUS.get('storage3x', [])},
        'wiring': [wire('storage3x', "require('./storage-guard.js')(null, %s);" % SDK_ARG, WEB_ADAPTER, after=True)],
        'own_markers': [r'\blocalStorage\s*\.\s*(?:getItem|setItem)\s*=(?!=)',
                        r'\b(?:tt|TTMinis\s*\.\s*game)\s*\.\s*(?:getStorageSync|setStorageSync)\s*=(?!=)'],
        'policy': {'new': 'replace', 'legacy': 'none'},
        'note': 'AFTER web-adapter.js: window.localStorage only exists once web-adapter ran, and the 3.x engine '
                'reads sys.localStorage = window.localStorage later, so guarding that object covers the engine. '
                'File owned by W-A1 (parts/storage-guard.js, same file as the 2.4 part).'}
    parts['rewardguard3x'] = {   # 生成时预防 R4G2 (R4A 没做完的 3.x guard; the name rewarded3x is RewardedService.plugin.js)
        'engine': 3, 'phase': 'native', 'step': 'rewardguard',
        'file': {'src': REWARD_GUARD_SRC, 'dest': 'rewarded-guard.js',
                 'template': 'build-templates/bytedance-mini-game/rewarded-guard.js',
                 'sha256': sha256(read(REWARD_GUARD_SRC)), 'previous_sha256': PREVIOUS.get('rewardguard3x', [])},
        'wiring': [wire('rewardguard3x', "require('./rewarded-guard.js')(null, %s);" % SDK_ARG, WEB_ADAPTER,
                        after=True)],
        'own_markers': [],
        'policy': {'new': 'replace', 'legacy': 'none'},
        'note': 'AFTER web-adapter.js, the same place as storage3x; before any game script calls '
                'createRewardedVideoAd. Same file and sha as the 2.4 part rewarded24, so the package checks '
                '(ads_static.kit_guard_hashes) treat an unchanged copy as kit code, not a game ad caller. cc is null: '
                'the guard follows the platform onHide / onShow only. Installed by tiktok_finalize (startup step: '
                'source wires a 3.x build-templates game.js, native / sync --native the build game.js). Legacy games: '
                'not installed. Node-tested (scripts/test_rewardguard3x.py); 待真机复测.'}
    parts['hostshim3x'] = {
        'engine': 3, 'phase': 'native', 'step': 'hostshim',
        'file': {'src': HOSTSHIM_SRC, 'dest': 'host-shim.js',
                 'template': 'build-templates/bytedance-mini-game/host-shim.js',
                 'sha256': sha256(read(HOSTSHIM_SRC)), 'previous_sha256': PREVIOUS.get('hostshim3x', [])},
        'wiring': [wire('hostshim3x', "require('./host-shim.js').install(%s);" % SDK_ARG, WEB_ADAPTER)],
        'own_markers': [],
        'policy': {'new': 'replace', 'legacy': 'report'},
        'note': 'BEFORE web-adapter.js (the adapter reads getOpenDataContext / SDKVersion when it loads). Fills only '
                'missing host APIs, never replaces one. Same file as the 2.4 part hostshim24. Installed by '
                'tiktok_finalize (source: build-templates game.js when the project has one; native / sync --native: '
                'the build game.js). Legacy games: report only.'}
    parts['boot3x'] = {
        'engine': 3, 'phase': 'native', 'step': 'boot',
        'file': {'src': BOOT_SRC, 'dest': 'boot-guard-3x.js',
                 'template': 'build-templates/bytedance-mini-game/boot-guard-3x.js',
                 'sha256': sha256(read(BOOT_SRC)), 'previous_sha256': PREVIOUS.get('boot3x', [])},
        'wiring': [wire('boot3x', "require('./boot-guard-3x.js').install(null, %s);" % SDK_ARG, SYSTEM_WARMUP)],
        'own_markers': BOOT_OWN,
        'policy': {'new': 'replace', 'legacy': 'report'},
        'note': "right BEFORE System.warmup(: hooks the first System.import('cc') and re-applies the file guard before "
                'every startup step. Numbers = 2.4 main.js v1.6. A game with its own start page (game.js loads '
                './boot-loading, or a root boot-loading.js / native-recovery.js) is reported, never stacked. '
                'Node-tested (tests/boot-3x.test.js); 待真机复测 on 3.7.1 / 3.8.8.'}
    doc = {'name': 'TikTokPlatformKit-Cocos3x-parts', 'version': KIT_VERSION, 'engine': 3,
           'generated_by': 'tools/make_plugin_scripts.py (do not edit; run it again)',
           'startup': 'boot3x: parts-3x/boot-guard-3x.js (new 3.x games: installed by tiktok_finalize; legacy games '
                      'and games with their own boot-loading start page: report only)',
           'plugin_meta_flags': PLUGIN_META_FLAGS,   # R4N6: checked on every plugin .meta at the end of sync
           'parts': parts}
    return (json.dumps(doc, indent=2, ensure_ascii=False, sort_keys=False) + '\n').encode('utf-8')


def generate():
    """{kit relpath: bytes} of every generated file."""
    plugins = {}
    for name, _, editable in MODULES:
        plugins[name] = render_plugin(name, read(src_of(name)), editable)
    for name, _, eager in PART_PLUGINS:   # 生成时预防 R4G2
        plugins[name] = render_plugin(name, read('%s/%s.js' % (PART_SRC_DIR, name)), False, PART_SRC_DIR, eager)
    out = {'%s/%s.plugin.js' % (OUT_DIR, n): b for n, b in plugins.items()}
    out[PARTS_FILE] = render_parts(plugins)
    return out


def check():
    """[problem strings]; empty = every generated file is current and every plugin core is byte-identical."""
    problems = []
    for name, src_dir in [(m[0], None) for m in MODULES] + [(m[0], PART_SRC_DIR) for m in PART_PLUGINS]:
        rel = '%s/%s.plugin.js' % (OUT_DIR, name)
        path = KIT / rel
        if not path.is_file():
            problems.append('%s missing' % rel)
            continue
        core = extract_core(name, path.read_bytes(), src_dir)
        src = '%s/%s.js' % (src_dir, name) if src_dir else src_of(name)
        source = read(src)
        if core is None:
            problems.append('%s: BEGIN/END lines missing or repeated' % rel)
        elif core != source:
            problems.append('%s: code between BEGIN and END differs from %s (sha %s vs %s)'
                            % (rel, src, sha256(core)[:12], sha256(source)[:12]))
    problems += slots_problems()   # R4G1
    try:
        wanted = generate()
    except (OSError, ValueError) as error:
        return problems + ['cannot generate: %s' % error]
    for rel, data in sorted(wanted.items()):
        path = KIT / rel
        if path.is_file() and path.read_bytes() != data and not any(p.startswith(rel) for p in problems):
            problems.append('%s is stale: run python3 tools/make_plugin_scripts.py' % rel)
        elif not path.is_file() and not any(p.startswith(rel) for p in problems):
            problems.append('%s missing' % rel)
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--check', action='store_true', help='write nothing; exit 1 when a generated file is stale')
    args = ap.parse_args(argv)
    if args.check:
        problems = check()
        print(json.dumps({'tool': 'make_plugin_scripts', 'mode': 'check', 'ok': not problems,
                          'problems': problems}, ensure_ascii=False, indent=2))
        return 1 if problems else 0
    written = []
    for rel, data in sorted(generate().items()):
        path = KIT / rel
        if path.is_file() and path.read_bytes() == data:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        written.append({'file': rel, 'sha256': sha256(data)})
    print(json.dumps({'tool': 'make_plugin_scripts', 'mode': 'write', 'written': written}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
