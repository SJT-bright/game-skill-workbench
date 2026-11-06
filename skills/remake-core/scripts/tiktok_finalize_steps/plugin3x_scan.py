"""Sync / source step (read only, under 1 s): Cocos 3.x kit parts are plugin scripts, never ES modules
(生成时预防 Round 4 R4N6, 问题普查补查2 第 11 组).

Census: 合成进化恐龙's EnglishRuntime did `import RunSession from '../tiktok-platform/RunSession'` and the first build
had 55 unresolved-module errors; 奔跑吧巨人 started without TikTokKit (RewardedService not registered) and the
session added side-effect imports of the plugin files. A 3.x kit part (plugins-3x/*.plugin.js, RunSession / FxPool /
ShopTx from sync) is imported as a plugin script: its .meta carries isPlugin, loadPluginInWeb, loadPluginInNative and
loadPluginInMiniGame (kit_sources / sync_run_parts write them), it runs before the game scripts and publishes
globalThis.TikTokKit.<Name> (RunSession: TikTokRunSession, FxPool: TikTokFxPool, ShopTx: TikTokShopTx). Game code uses
those globals only. GameUIKit.ts is the one 3.x kit file that IS a module (`import GameUIKit from
'../tiktok-platform/GameUIKit'`), so only an import of GameUIKit.js / GameUIKit.plugin counts.

  K_plugin3x_import  a game script (assets/**/*.ts|js outside assets/tiktok-platform/) imports or requires a kit plugin
                     module by path. New remake games: block; English games (board localize): warning; legacy: info.
  K_plugin3x_meta    a kit plugin file in the project whose .meta misses one of the four flags (or has no .meta).
                     New games: block (sync has just written them, so something overwrote them); legacy: info.
Runs at the END of `tiktok_finalize.py sync` (after sync_run_parts wrote RunSession / FxPool / ShopTx) and in source.
2.4: n/a. The flag values come from parts-3x/KIT_PARTS_3X.json "plugin_meta_flags" (make_plugin_scripts.py
PLUGIN_META_FLAGS); a line carrying `// tiktok-kit:plugin-ok <why>` is skipped.
"""
import json
import re
import time
from pathlib import Path

from . import Result

STEP = 'plugin3x_scan'
FLAGS = {'isPlugin': True, 'loadPluginInWeb': True, 'loadPluginInNative': True, 'loadPluginInMiniGame': True}
DEFAULT_NAMES = {'PlatformConfig', 'TikTokMissionService', 'RewardedService', 'SaveStore', 'MissionFlow',
                 'HomeEntrySlots', 'CapsuleLayout', 'CapsuleAuto', 'RunSession', 'FxPool', 'ShopTx', 'SaveSchema'}
MODULE_ONLY = {'GameUIKit'}          # a real 3.x module (parts-3x/GameUIKit.ts): only .js / .plugin imports count
KIT_DIR = 'assets/tiktok-platform/'
EXEMPT = 'tiktok-kit:plugin-ok'
IMPORT = re.compile(r'''^\s*(?:import\s+(?:[^'";]*?\s+from\s+)?|export\s+[^'";]*?\s+from\s+|.*?\brequire\s*\(\s*|'''
                    r'''.*?\bimport\s*\(\s*)['"]([^'"\n]+)['"]''')
SKIP_PARTS = ('/library/', '/temp/', '/build/', 'node_modules/')


def _target(spec):
    """(module name, kind): kind 'plugin' for X.plugin(.js), 'js' for X.js, '' for a bare X."""
    last = spec.rstrip('/').rsplit('/', 1)[-1]
    if last.endswith('.plugin.js'):
        return last[:-len('.plugin.js')], 'plugin'
    if last.endswith('.plugin'):
        return last[:-len('.plugin')], 'plugin'
    for ext in ('.js', '.ts', '.mjs'):
        if last.endswith(ext):
            return last[:-len(ext)], ext[1:]
    return last, ''


def _own_module(root, rel, spec):
    """True when the import resolves to the game's own script (Marlows' own PlatformConfig.ts), not a kit file."""
    if root is None or not spec.startswith('.'):
        return False
    base = (Path(root) / rel).parent / spec
    for cand in (base, Path(str(base) + '.ts'), Path(str(base) + '.js')):
        try:
            crel = cand.resolve().relative_to(Path(root).resolve()).as_posix()
        except (ValueError, OSError):
            continue
        if cand.is_file() and not crel.startswith(KIT_DIR) and not crel.endswith('.plugin.js'):
            return True
    return False


def import_hits(text, rel, names, root=None):
    raw = text.split('\n')
    out = []
    for ln, line in enumerate(raw, 1):
        stripped = line.lstrip()
        if stripped.startswith('//') or stripped.startswith('*'):
            continue
        if any(EXEMPT in raw[k] for k in (ln - 1, ln - 2) if 0 <= k < len(raw)):
            continue
        m = IMPORT.match(line)
        if not m or not (m.group(1).startswith('.') or '/' in m.group(1)):
            continue
        name, kind = _target(m.group(1))
        if _own_module(root, rel, m.group(1)):
            continue
        if (name in names and name not in MODULE_ONLY) or (name in MODULE_ONLY and kind in ('plugin', 'js')):
            out.append({'file': rel, 'line': ln, 'module': name, 'code': line.strip()[:140]})
    return out


def names_and_plugins(manifest):
    """(module names, [plugin file relpaths in a project]) from KIT_MANIFEST (+ KIT_PARTS_3X), or the defaults."""
    names, dests = set(DEFAULT_NAMES), []
    if manifest is None:
        return names, None
    for name, part in manifest.parts_for(3, 'source'):
        dest = (part.get('file') or {}).get('dest') or ''
        if part.get('plugin') and dest:
            names.add(_target(dest)[0])
            dests.append(dest)
    for key, spec in sorted(manifest.files.items()):
        if isinstance(spec, dict) and isinstance(spec.get('sync_install'), dict) and spec['sync_install'].get('plugin_3x'):
            names.add(_target(spec['project_path'])[0])
            dests.append(spec['project_path'])
    return names, dests


def flags_of(manifest):
    if manifest is None:
        return dict(FLAGS)
    for inc in manifest.included:
        try:
            data = json.loads((manifest.kit_dir / inc).read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if isinstance(data.get('plugin_meta_flags'), dict):
            return data['plugin_meta_flags']
    return dict(FLAGS)


def meta_problem(meta_bytes, flags=None):
    flags = flags or FLAGS
    if meta_bytes is None:
        return 'no .meta (missing)'
    try:
        user = (json.loads(meta_bytes.decode('utf-8')) or {}).get('userData') or {}
    except (ValueError, UnicodeDecodeError, AttributeError):
        return '.meta is not JSON'
    bad = [k for k, v in flags.items() if user.get(k) is not v]
    return ('.meta lacks %s' % ', '.join(bad)) if bad else None


def scan(root, manifest=None):
    started = time.time()
    root = Path(root)
    names, dests = names_and_plugins(manifest)
    flags = flags_of(manifest)
    found = {'files': 0, 'imports': [], 'metas': [], 'plugins': 0}
    base = root / 'assets'
    for p in sorted(base.rglob('*')) if base.is_dir() else []:
        rel = p.relative_to(root).as_posix()
        if not p.is_file() or p.suffix not in ('.ts', '.js') or rel.startswith(KIT_DIR) or rel.endswith('.d.ts') \
                or any(s in '/' + rel for s in SKIP_PARTS) or p.stat().st_size > 300 * 1024:
            continue
        found['files'] += 1
        found['imports'] += import_hits(p.read_text(encoding='utf-8', errors='replace'), rel, names, root)
    if dests is None:
        dests = [p.relative_to(root).as_posix() for p in sorted((root / KIT_DIR).glob('*.plugin.js'))] \
            if (root / KIT_DIR).is_dir() else []
    for rel in dests:
        if not (root / rel).is_file():
            continue
        found['plugins'] += 1
        meta = root / (rel + '.meta')
        why = meta_problem(meta.read_bytes() if meta.is_file() else None, flags)
        if why:
            found['metas'].append({'file': rel, 'problem': why})
    found['seconds'] = round(time.time() - started, 3)
    return found


def findings(found, policy='new', board='remake'):
    out = []
    if found['imports']:
        level = 'info' if policy == 'legacy' else ('warn' if board == 'localize' else 'block')
        shown = '; '.join('%s:%d %s' % (x['file'], x['line'], x['code']) for x in found['imports'][:6])
        out.append({'id': 'K_plugin3x_import', 'level': level,
                    'message': '%d game script line(s) import a 3.x kit plugin by path (Cocos 3.x cannot resolve a '
                               'plugin script as a module: 合成进化恐龙 55 unresolved-module): %s. Delete the import and '
                               'use globalThis.TikTokKit.<Name> (RunSession: TikTokRunSession, FxPool: TikTokFxPool, '
                               'ShopTx: TikTokShopTx); the plugin loads by itself' % (len(found['imports']), shown),
                    'evidence': found['imports'][:30]})
    if found['metas']:
        level = 'info' if policy == 'legacy' else 'block'
        out.append({'id': 'K_plugin3x_meta', 'level': level,
                    'message': '%d kit plugin file(s) not imported as plugin (isPlugin + loadPluginInWeb / Native / '
                               'MiniGame): %s. Run tiktok_finalize.py sync again; do not edit the .meta by hand'
                               % (len(found['metas']), '; '.join('%s %s' % (m['file'], m['problem'])
                                                                 for m in found['metas'][:6])),
                    'evidence': found['metas'][:30]})
    return out


# R4R4 (R4Q5 留下的, 奔跑吧巨人 is 3.x): the 3.x PlatformConfig ids get the same check as the 2.4 one in
# platform-kit/tools/check_kit_project.py - the same foreign_config_findings is called, not a copy. The shared TikTok
# test app of the kit template (App ID 7683427172773644296 and its 3 ad units, Saul 2026-10-29) passes; an appId /
# clientKey / ad unit that is neither the shared app nor in docs/platform/platform_ids.json and that another game
# (peers) carries: K_platform_ids_foreign (new remake: block, English: warning, legacy: info); a shared gameId and
# unrecorded ids: K_W_platform_ids (warning, legacy: info). Peers: ctx.options['peers'] or TIKTOK_KIT_PEERS
# (folders separated by os.pathsep); none given = only the shared app and the record are checked.
PLATFORM_CONFIG_3X = ('assets/tiktok-platform/PlatformConfig.plugin.js', 'assets/tiktok-platform/PlatformConfig.js',
                      'assets/tiktok-platform/PlatformConfig.ts')
_CKP = {}


def _check_kit_project(kit_dir=None):
    import importlib.util
    path = Path(kit_dir) / 'tools' / 'check_kit_project.py' if kit_dir else \
        Path(__file__).resolve().parents[2] / 'assets' / 'platform-kit' / 'tools' / 'check_kit_project.py'
    if path not in _CKP:
        spec = importlib.util.spec_from_file_location('check_kit_project_r4r4', path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _CKP[path] = mod
    return _CKP[path]


def peers_of(ctx):
    import os
    raw = (getattr(ctx, 'options', None) or {}).get('peers') or os.environ.get('TIKTOK_KIT_PEERS') or []
    if isinstance(raw, str):
        raw = [x for x in raw.split(os.pathsep) if x]
    return [Path(x) for x in raw]


def platform_id_findings(root, manifest=None, peers=None, policy='new', board='remake'):
    root = Path(root)
    rel = next((r for r in PLATFORM_CONFIG_3X if (root / r).is_file()), None)
    if not rel:
        return []
    ckp = _check_kit_project(getattr(manifest, 'kit_dir', None))
    errors, warnings = ckp.foreign_config_findings(root, (root / rel).read_text(encoding='utf-8', errors='replace'), peers)
    out = []
    if errors:
        level = 'info' if policy == 'legacy' else ('warn' if board == 'localize' else 'block')
        out.append({'id': 'K_platform_ids_foreign', 'level': level,
                    'message': '%s: %s' % (rel, '; '.join(errors)), 'evidence': errors[:10]})
    if warnings:
        out.append({'id': 'K_W_platform_ids', 'level': 'info' if policy == 'legacy' else 'warn',
                    'message': '%s: %s' % (rel, '; '.join(warnings)), 'evidence': warnings[:10]})
    return out


def _all_findings(ctx, found):
    out = findings(found, ctx.policy, ctx.board)
    try:
        out += platform_id_findings(ctx.root, ctx.manifest, peers_of(ctx), ctx.policy, ctx.board)
    except Exception as e:   # the id check never breaks the plugin scan
        out.append({'id': 'K_W_platform_ids', 'level': 'warn', 'message': 'platform id check could not run: %s' % e})
    return out


def detect(ctx):
    if ctx.engine != 3:
        return 'n/a'
    found = scan(ctx.root, ctx.manifest)
    if findings(found, ctx.policy, ctx.board):
        return 'conflict'
    return 'conflict' if any(x['level'] == 'block' for x in _all_findings(ctx, found)) else 'kit_current'


def apply(ctx):
    r = Result(STEP)
    if ctx.engine != 3:
        r.state = 'n/a'
        return r.as_dict()
    found = scan(ctx.root, ctx.manifest)
    for item in _all_findings(ctx, found):   # R4R4: + the 3.x PlatformConfig id check
        if item['level'] == 'block':
            r.blocks.append(item)
        elif item['level'] == 'warn':
            r.warnings.append(item)
        else:
            r.info.append('%s (report only): %s' % (item['id'], item['message']))
    r.state = 'kit_current' if not r.blocks else 'conflict'
    r.info.append('%d script(s), %d kit plugin file(s) checked in %.2f s; %d import line(s), %d .meta problem(s)'
                  % (found['files'], found['plugins'], found['seconds'], len(found['imports']), len(found['metas'])))
    return r.as_dict()


def verify(files, manifest=None, policy=None):
    return []
