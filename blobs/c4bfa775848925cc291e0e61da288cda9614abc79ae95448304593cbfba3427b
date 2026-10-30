"""Platform-kit standard parts are really in the package (v7.7, design D77 1.5). READ ONLY.

Runs in every entry through package_gates.run() (both writers and check_package). It reads the package bytes and
KIT_MANIFEST.json (kit 2.0 `parts` + includes), never a record or what the game says about itself:
    K1_kit_bytes      each applicable native part file is in the package with the manifest sha256
    K2_kit_wiring     its load line is there exactly once on the right side of the manifest anchor; with the kit
                      main.js, game.js really requires './main' exactly once (Nanas)
    K3_single_layer   no second touch / storage layer (own_markers / own_files, kit hashes excluded)
    K2_login          new 2.4 games: the kit main.js login line, or the game's own login call
    K_appid_*         project.config.json appid is a real TikTok App ID
    K_S_* / L4_debug_code / W_duplicate_files   structure checks (tiktok_finalize_steps/structure.py)
Writers only (the view carries finalize_record / writer=True: package_gates.run(..., context=...), W-D1):
    K4_finalize_ran   the native record of this run exists, has no block, its written bytes are in the package
    K5_source_finalized  the project's source record matches the project and the kit version, and its recorded
                      options (--keep-webp-exception reason) equal the writer's finalize_options (W-D1 request 3)
    K_webp_exception_3x  a writer passed --keep-webp-exception for a 3.x build (no 3.x WebP exception in v7.7)
    K1_plugin3x       (v7.7 W-D1, W-D4 request 5) new 3.x games: src/settings.json plugins.jsList lists every kit plugin
                      script (assets/tiktok-platform/<Name>.plugin.js) and each listed file keeps its
                      // tiktok-kit:plugin3x:<Name>: marker and its ---- BEGIN / ---- END lines (Creator re-wraps and
                      strips the files, so bytes are not compared)
    K_platform_config new games: PlatformConfig (2.4 module PlatformConfig, 3.x PlatformConfig.plugin.js BEGIN..END,
                      in the package and, for a writer, in <project>/assets/tiktok-platform/) no longer has the
                      template gameId ('change-me' / empty) and has normalLevelCoins > 0; otherwise add-to-home and
                      revisit pay 0 instead of 5B. Legacy games: warning.
Source-phase parts (2.4 modules, 3.x plugin scripts) are not byte-checked here: Creator may minify or rename them in a
build, so they are proven by the source record (kit_sources.py, W-A2 request 2).

Policy: view.policy when the caller sets it ('new' | 'legacy'); otherwise decided from the package itself
(tiktok_finalize_steps.policy.decide(files=...): scene / asset uuids against LEGACY_GAMES.json, default new).
new: every finding above that the design marks 'block' blocks. legacy: only lines finalize itself inserted
(marked // tiktok-kit:<part>:<version>) are held to K1/K2; own layers are warnings.
"""
import sys
from pathlib import Path

from . import finding

SCRIPTS = Path(__file__).resolve().parent.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _policy(view):
    get = getattr(view, 'get_policy', None)
    if get is not None:                      # package_gates.PackageView (v7.7): caller's policy or judged once
        return get()
    from tiktok_finalize_steps import policy as P
    given = getattr(view, 'policy', None)
    if given in ('new', 'legacy'):
        return given, 'given by the caller'
    rec = getattr(view, 'finalize_record', None)
    if isinstance(rec, dict) and rec.get('policy') in ('new', 'legacy'):
        return rec['policy'], "from this run's finalize record"
    out = P.decide(files=view.files)
    return out['policy'], out['reason']


# Cocos 3.x engine files (cocos-js/) are never scanned for a second touch / storage layer (W-A2 request 1): the engine
# has member assignments such as e.onTouchStart=function..., and scanning it is slow. 2.4 engine files are skipped by
# tiktok_finalize_steps.is_engine_or_adapter already.
ENGINE_DIRS = ('cocos-js/',)


def layer_files(files):
    return {k: v for k, v in files.items() if not (k.startswith(ENGINE_DIRS) and k.endswith('.js'))}


import json  # noqa: E402
import re  # noqa: E402

PLUGIN_MARK = '// tiktok-kit:plugin3x:%s:'
GAME_ID = re.compile(r'\bgameId\s*:\s*(["\'])(.*?)\1')
LEVEL_COINS = re.compile(r'\bnormalLevelCoins\s*:\s*(-?[0-9]+(?:\.[0-9]+)?)')
PLACEHOLDER_IDS = ('', 'change-me')
KIT_CONFIG_MARK = re.compile(r'growthReward|GROWTH_REWARD_B|normalLevelCoins')
BEGIN_END = re.compile(r'---- BEGIN [^\n]*?PlatformConfig\.js ----(.*?)---- END', re.S)


def kit_plugins(manifest):
    """[(name, dest)] of the 3.x kit plugin parts, e.g. ('MissionFlow', 'assets/tiktok-platform/MissionFlow.plugin.js')."""
    out = []
    for _, part in manifest.parts_for(3, 'source'):
        dest = (part.get('file') or {}).get('dest') or ''
        if part.get('plugin') and dest.endswith('.plugin.js'):
            out.append((dest.rsplit('/', 1)[-1][:-len('.plugin.js')], dest))
    return sorted(out)


def plugin_findings(files, manifest, policy):
    plugins = kit_plugins(manifest)
    if not plugins:
        return []
    level = 'block' if policy == 'new' else 'warn'
    try:
        settings = json.loads(files.get('src/settings.json', b'{}').decode('utf-8-sig'))
        js_list = list(((settings.get('plugins') or {}).get('jsList')) or [])
    except (ValueError, UnicodeDecodeError, AttributeError):
        js_list = []
    out = []
    for name, dest in plugins:
        if dest not in js_list:
            out.append(finding('K1_plugin3x', level, 'kit plugin %s is not in src/settings.json plugins.jsList (its '
                               '.meta must keep "import as plugin" for native and mini-game)' % dest,
                               {'plugin': name}))
            continue
        text = files.get('src/' + dest, b'').decode('utf-8', 'replace')
        missing = [m for m in (PLUGIN_MARK % name, '---- BEGIN', '---- END') if m not in text]
        if missing:
            out.append(finding('K1_plugin3x', level, 'kit plugin src/%s %s' % (
                dest, 'is not in the package' if not text else 'lost %s' % ', '.join(missing)), {'plugin': name}))
    return out


def platform_config_problems(text):
    """Template values left in a PlatformConfig text (2.4 module or 3.x plugin BEGIN..END), as short strings."""
    m = BEGIN_END.search(text)
    body = m.group(1) if m else text
    out = []
    gid = GAME_ID.search(body)
    if not gid:
        out.append('gameId not found')
    elif gid.group(2).strip() in PLACEHOLDER_IDS:
        out.append('gameId is the template value %r' % gid.group(2))
    coins = LEVEL_COINS.search(body)
    if not coins:
        out.append('normalLevelCoins not found')
    elif float(coins.group(1)) <= 0:
        out.append('normalLevelCoins is %s (must be this game\'s B > 0)' % coins.group(1))
    return out


def platform_config_texts(view):
    """[(where, text)]: the PlatformConfig module(s) in the package and, for a writer, in the project."""
    from .ads_static import kit_module_name, modules
    # only the kit's PlatformConfig (a game module that merely has the name is not it): kit 2.0 text marks
    out = [('package %s (%s)' % (f, m), t) for f, m, t in modules(view)
           if kit_module_name(m) == 'PlatformConfig' and KIT_CONFIG_MARK.search(t)]
    project = getattr(view, 'project', None)
    if project:
        for rel in ('assets/tiktok-platform/PlatformConfig.js', 'assets/tiktok-platform/PlatformConfig.plugin.js'):
            path = Path(project) / rel
            if path.is_file():
                out.append(('project ' + rel, path.read_text(encoding='utf-8', errors='replace')))
    return out


def config_findings(view, policy):
    out = []
    level = 'block' if policy == 'new' else 'warn'
    for where, text in platform_config_texts(view):
        problems = platform_config_problems(text)
        if problems:
            out.append(finding('K_platform_config', level, '%s: %s; add-to-home and revisit would pay 0 instead of 5B '
                               '(set gameId and normalLevelCoins = B in PlatformConfig)' % (where, '; '.join(problems)),
                               {'where': where, 'problems': problems}))
    return out


def check(view):
    import tiktok_finalize_steps as T
    from tiktok_finalize_steps import appid, login, startup, storage, structure, touch
    try:
        manifest = T.load_manifest()
    except T.KitError as error:
        return [finding('K_kit_unusable', 'block', str(error))]
    engine = view.engine_major
    if engine not in (2, 3):
        # v7.7.4 (总表 B18): an unrecognised engine used to skip every standard-part check without a word.
        policy, why = _policy(view)
        return [finding('K_engine_unknown', 'block' if policy == 'new' else 'warn',
                        'no Cocos 2.4 / 3.x engine file recognised (renamed, or not a Cocos mini-game build), so no '
                        'platform-kit standard part could be checked', {'policy': policy, 'why': why})]
    if not manifest.has_parts():
        return [finding('K_kit_unusable', 'block', 'KIT_MANIFEST.json %s has no parts section (kit 2.0 needed)'
                        % manifest.version)]
    policy, why = _policy(view)
    files = view.files
    out = []
    out += startup.verify(files, manifest, policy, engine)
    out += touch.verify(layer_files(files), manifest, policy, engine)
    out += storage.verify(layer_files(files), manifest, policy, engine)
    out += login.verify(files, manifest, policy, engine)
    out += appid.verify(files, manifest, policy)
    out += structure.verify(files, manifest, policy, getattr(view, 'finalize_options', None))
    if engine == 3 and policy == 'new':
        out += plugin_findings(files, manifest, policy)
    out += config_findings(view, policy)
    if getattr(view, 'writer', False) or getattr(view, 'finalize_record', None) is not None:
        import tiktok_finalize as F
        options = getattr(view, 'finalize_options', None) or {}    # a writer without options used none
        out += F.check_finalize_record(getattr(view, 'finalize_record', None), files)
        out += F.check_source_record(getattr(view, 'project', None), manifest, options=options)
        out += F.webp_exception_3x(engine, options)
    for item in out:
        item.setdefault('evidence', {})
        if isinstance(item['evidence'], dict):
            item['evidence'].setdefault('policy', policy)
    if out:
        out.append(finding('K_policy', 'warn', 'kit_parts ran with policy %s (%s)' % (policy, why)))
    return out
