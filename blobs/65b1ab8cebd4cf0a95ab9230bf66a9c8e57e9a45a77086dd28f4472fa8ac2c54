"""Growth missions and login (v7.5, Mabel's Meadow problem 1 and 6, MusicSlice problem 9).

G1_growth_apis (block): the game JavaScript (engine and platform adapter excluded) must contain all five
TikTok growth calls: addShortcut, getShortcutMissionReward, startEntranceMission, getEntranceMissionReward and
canReceiveReward. Add to Home Screen and Profile Revisit are mandatory TikTok capabilities; a package that only
jumps (addShortcut / startEntranceMission) but never asks for the reward is refused too. This reads the package
bytes only and never depends on what the game declares about its features.

G1k_growth_outside_kit (v7.7, design D77 1.5 / 3.7): game JavaScript calls a growth-mission SDK method
(addShortcut, checkShortcut, startEntranceMission, getShortcutMissionReward, getEntranceMissionReward) in a module
other than the platform kit's TikTokMissionService / MissionFlow (2.4 modules, or their 3.x .plugin.js scripts; a
kit module is recognised by name AND by the fingerprint KIT_MANIFEST parts.missions.modules gives it). Block for a
NEW game, warning for a game on the frozen legacy list (view.get_policy()), the same rule as A1_rewarded_outside_kit.

W2_login (warn): no TikTok login call. 8 of 14 completed games never call login, so this stays a warning until
Saul decides otherwise.
"""
import re

from . import finding

MISSION_APIS = ('addShortcut', 'getShortcutMissionReward', 'startEntranceMission', 'getEntranceMissionReward',
                'canReceiveReward')
LOGIN = re.compile(r'\.login\s*\(|\[\s*["\']login["\']\s*\]')
GROWTH_CALLS = ('addShortcut', 'checkShortcut', 'startEntranceMission', 'getShortcutMissionReward',
                'getEntranceMissionReward')
G1K_LEVELS = {'new': 'block', 'legacy': 'warn'}
# Fallback when KIT_MANIFEST.json cannot be read: the kit 2.0 fingerprints (parts.missions.modules).
KIT_MODULES = {'MissionFlow': r'Add this game to your home screen, open it from the new icon, then come back for '
                              r'your reward\.',
               'TikTokMissionService': r'Return through this TikTok entry, then check your reward\.'}


def growth_call_rx(names=GROWTH_CALLS):
    alt = '|'.join(re.escape(n) for n in names)
    # a member call x.addShortcut( / x.addShortcut.call( or an indexed call x['addShortcut'](; method definitions
    # (addShortcut: function / addShortcut() {) and plain strings are not calls of the SDK.
    return re.compile(r'\.\s*(%s)\s*(?:\.\s*(?:call|apply)\s*)?\(|\[\s*["\'](%s)["\']\s*\]\s*\(' % (alt, alt))


def kit_fingerprints():
    """{module name: compiled fingerprint} from KIT_MANIFEST parts.missions (+ sdk_calls), fallback KIT_MODULES."""
    modules, calls = dict(KIT_MODULES), GROWTH_CALLS
    try:
        import sys
        from pathlib import Path
        scripts = str(Path(__file__).resolve().parent.parent)
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        import tiktok_finalize_steps as T
        part = T.load_manifest().part('missions') or {}
        if isinstance(part.get('modules'), dict) and part['modules']:
            modules = dict(part['modules'])
        if part.get('sdk_calls'):
            calls = tuple(part['sdk_calls'])
    except Exception:  # noqa: BLE001 - the built-in kit 2.0 fingerprints still apply
        pass
    return {k: re.compile(v) for k, v in modules.items()}, calls


def _policy(view):
    get = getattr(view, 'get_policy', None)
    return get()[0] if get else 'new'


def outside_kit_calls(view):
    """[(file, module, [calls])] of growth SDK calls outside the kit modules."""
    from .ads_static import kit_module_name, modules
    prints, calls = kit_fingerprints()
    rx = growth_call_rx(calls)
    out = []
    for name, module, text in modules(view):
        hits = sorted({m.group(1) or m.group(2) for m in rx.finditer(text)})
        if not hits:
            continue
        base = kit_module_name(module)
        if base in prints and prints[base].search(text):
            continue
        out.append((name, module, hits))
    return out


def check(view):
    names = view.game_js()
    blob = '\n'.join(view.text(n) for n in names)
    out = []
    missing = [api for api in MISSION_APIS if api not in blob]
    if missing:
        present = [api for api in MISSION_APIS if api not in missing]
        out.append(finding(
            'G1_growth_apis', 'block',
            'game JS is missing %s; Add to Home Screen and Profile Revisit (with their reward queries) are mandatory '
            'TikTok capabilities' % ', '.join(missing),
            {'missing': missing, 'present': present, 'game_js_files': len(names)}))
    outside = outside_kit_calls(view)
    if outside:
        level = G1K_LEVELS.get(_policy(view), 'block')
        out.append(finding(
            'G1k_growth_outside_kit', level,
            'game code calls the growth-mission SDK outside the platform kit TikTokMissionService / MissionFlow: %s%s'
            % (', '.join('%s %s (%s)' % (m, '/'.join(c), f) for f, m, c in outside[:6]),
               '; a new game must use MissionFlow / HomeGrowthEntries (2.4) or globalThis.TikTokKit.MissionFlow (3.x)'
               if level == 'block' else ''),
            {'modules': ['%s:%s:%s' % (f, m, ','.join(c)) for f, m, c in outside], 'policy': _policy(view)}))
    if not LOGIN.search(blob):
        out.append(finding('W2_login', 'warn',
                           'no TikTok login call found (TikTok code scan asks for the Login API; fire-and-forget is enough)'))
    return out
