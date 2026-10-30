"""Static rewarded-ad code gates (v7.5, Basil problem 1.3).

A1_rewarded_outside_kit: game JavaScript calls createRewardedVideoAd in a module other than the platform kit's
    RewardedService (2.4 module, or the 3.x plugin script RewardedService.plugin.js). v7.7 (design D77 1.5, 3.3):
    block for a NEW game, warning for a game on the frozen legacy list (view.get_policy(); see A1_LEVELS). The
    mandatory ad regression still covers behaviour.
A2_hide_kills_ad: an EVENT_HIDE / onHide handler cancels, destroys or unbinds the rewarded ad (directly, or by
    calling a method of the module that creates rewarded ads whose body does so). TikTok can send the game to the
    background while the full-screen ad plays, so every finished video would grant nothing (remake: block; other
    boards: warning).
Ad timing (timeouts) is not checked here; it is on hold.
"""
import re

from . import finding

KIT_MODULE = 'RewardedService'
# The kit module looks the SDK up through its own getSDK('createRewardedVideoAd'); a game module that is merely
# named RewardedService (TobinsGem's own timer-based one) is not the kit.
KIT_FINGERPRINT = re.compile(r'getSDK\(\s*["\']createRewardedVideoAd["\']\s*\)')
CREATE_CALL = re.compile(r'createRewardedVideoAd\s*(?:\.\s*(?:call|apply)\s*)?\(|\[\s*["\']createRewardedVideoAd["\']\s*\]\s*\(')
MODULE_2X = re.compile(r'cc\._RF\.push\(\s*\w+\s*,\s*["\'][^"\']*["\']\s*,\s*["\']([\w$.-]+)["\']')
MODULE_3X = re.compile(r'System\.register\(\s*["\']chunks:///_virtual/([\w$.-]+?)(?:\.ts|\.js)?["\']')
HIDE_ON = re.compile(r'\.(?:on|once)\(\s*(?:[\w$.]*\.)?EVENT_HIDE\s*,\s*|\bonHide\(\s*')
# Ending the ad session: finish('cancel...') / cancel callbacks, or destroy/offClose on an ad-named object.
# Generic .destroy() on nodes (an aim line, labels) is not an ad and must not count.
AD_OBJECT_KILL = re.compile(r'(?<![\w$])(?:_?ad|\w*(?:Ad|Video|Rewarded|Reward)\w*)\s*\.\s*(?:destroy|offClose|offError)\s*\(')
KILL = re.compile(r'finish\s*\(\s*["\']cancel|(?<![\w$])(?:_?ad|\w*(?:Ad|Video|Rewarded|Reward)\w*)\s*\.\s*'
                  r'(?:destroy|offClose|offError)\s*\(')


PLUGIN_SUFFIX = re.compile(r'\.plugin(?:\.[0-9a-f]{5,})?$')


def kit_module_name(module):
    """'RewardedService.plugin' (3.x plugin script file) -> 'RewardedService'; other names unchanged."""
    return PLUGIN_SUFFIX.sub('', module or '')


def _is_kit(module, text):
    return kit_module_name(module) == KIT_MODULE and bool(KIT_FINGERPRINT.search(text))


def _level(view):
    return 'block' if view.board == 'remake' else 'warn'


# v7.5 made A1 a warning on every board (blocking then would have refused 25 of 26 delivered self-made packs).
# v7.7 (Saul Q1 2026-10-29): every game not on the frozen legacy list is new, and a new game must use the kit's
# RewardedService, so A1 blocks new games; delivered games are on the legacy list and keep the v7.5 warning.
A1_LEVELS = {'new': 'block', 'legacy': 'warn'}
A1_LEVEL = A1_LEVELS['legacy']          # v7.5 name kept for callers that read it; the level now follows the policy


def a1_level(view):
    get = getattr(view, 'get_policy', None)
    policy = get()[0] if get else 'new'
    return A1_LEVELS.get(policy, 'block')


def modules(view):
    """[(file, module name, text)] - Cocos bundle files split per script module; other JS is one module."""
    out = []
    for name in view.game_js():
        text = view.text(name)
        marks = [(m.start(), m.group(1)) for m in MODULE_2X.finditer(text)] or \
                [(m.start(), m.group(1)) for m in MODULE_3X.finditer(text)]
        if not marks:
            stem = name.rsplit('/', 1)[-1]
            out.append((name, stem[:-3] if stem.endswith('.js') else stem, text))
            continue
        if marks[0][0] > 0:
            out.append((name, '<bundle head>', text[:marks[0][0]]))
        for i, (pos, mod) in enumerate(marks):
            end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
            out.append((name, mod, text[pos:end]))
    return out


def _block_after(text, pos, limit=6000):
    """The {...} body that starts at the first '{' at or after pos (strings skipped roughly)."""
    start = text.find('{', pos, pos + 400)
    if start < 0:
        return ''
    depth, i, quote = 0, start, None
    end = min(len(text), start + limit)
    while i < end:
        c = text[i]
        if quote:
            if c == '\\':
                i += 1
            elif c == quote:
                quote = None
        elif c in '"\'`':
            quote = c
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return text[start + 1:i]
        i += 1
    return text[start + 1:end]


def _method_bodies(text, name):
    bodies = []
    pattern = re.compile(r'(?:[\s,{;.]|^)%s\s*(?:[:=]\s*function\s*\([^)]*\)|\([^)]*\)\s*)\s*\{' % re.escape(name))
    for m in pattern.finditer(text):
        bodies.append(_block_after(text, m.end() - 1))
    return bodies


def _hide_handlers(text):
    """Bodies of EVENT_HIDE / onHide handlers in one module: inline functions, or named methods."""
    out = []
    for m in HIDE_ON.finditer(text):
        rest = text[m.end(): m.end() + 200]
        inline = re.match(r'\s*(?:function\s*\w*\s*\([^)]*\)|\([^)]*\)\s*=>|\w+\s*=>)\s*\{?', rest)
        if inline:
            out.append(('inline', _block_after(text, m.end()) if inline.group(0).rstrip().endswith('{')
                        else rest[:200]))
            continue
        named = re.match(r'\s*(?:this|\w+)\.([\w$]+)\s*[,)]', rest) or re.match(r'\s*([\w$]+)\s*[,)]', rest)
        if named:
            for body in _method_bodies(text, named.group(1)):
                out.append((named.group(1), body))
    return out


def check(view):
    mods = modules(view)
    out = []
    ad_modules = [(f, m, t) for f, m, t in mods if 'createRewardedVideoAd' in t]
    outside = [(f, m) for f, m, t in ad_modules if CREATE_CALL.search(t) and not _is_kit(m, t)]
    if outside:
        level = a1_level(view)
        out.append(finding('A1_rewarded_outside_kit', level,
                           'game code creates rewarded ads outside the platform kit RewardedService: %s%s'
                           % (', '.join('%s (%s)' % (m, f) for f, m in outside[:6]),
                              '; a new game must call RewardedService.request() (2.4) / '
                              'globalThis.TikTokKit.RewardedService (3.x) instead' if level == 'block' else ''),
                           {'modules': ['%s:%s' % fm for fm in outside], 'policy': view.get_policy()[0]
                            if hasattr(view, 'get_policy') else None}))
    ad_texts = [t for f, m, t in ad_modules if not _is_kit(m, t)]
    hits = []
    for f, m, t in mods:
        if _is_kit(m, t):
            continue
        for handler, body in _hide_handlers(t):
            if AD_OBJECT_KILL.search(body):
                hits.append('%s/%s: %s' % (m, handler, AD_OBJECT_KILL.search(body).group(0)))
                continue
            for call in set(re.findall(r'\.([\w$]+)\s*\(', body)):
                for ad_text in ad_texts:
                    if any(KILL.search(b) for b in _method_bodies(ad_text, call)):
                        hits.append('%s/%s calls %s() which ends the rewarded ad' % (m, handler, call))
                        break
    if hits:
        out.append(finding('A2_hide_kills_ad', _level(view),
                           'an EVENT_HIDE/onHide handler ends the playing rewarded ad, so a video watched while '
                           'TikTok backgrounds the game grants nothing: %s' % '; '.join(sorted(set(hits))[:4]),
                           {'hits': sorted(set(hits))}))
    return out
