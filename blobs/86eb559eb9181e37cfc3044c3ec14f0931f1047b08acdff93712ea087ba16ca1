"""TikTok runtime compatibility gate (SimonsScrew research 2026-10-28, TikTok问题调研/调研总结.md section 4).

Static checks on the package bytes for causes of "scan the QR code and the game never opens" that the other gates
do not cover. Each rule names the public case it comes from.

block in both policies (the package cannot load or the TikTok CLI refuses it):
    T1_engine_plugin     game.json "plugins" holds the Douyin/WeChat separated-engine plugin (plugins.cocos, a tt.../wx...
                         provider, or no version). ttmg looks plugins up by name + version in TikTok's own library and
                         stops with "The current game plugin version does not exist"; the engine never loads.
                         Fix: build with "separate engine" off. Any other plugin is a warning (TikTok has engine
                         plugins since SDK 0.5.0, but the docs list none).
    T2_subpackages_key   game.json uses "subPackages" (or another casing) instead of lowercase "subpackages".
                         @ttmg/cli refuses it, and verify_native_zip reads only the lowercase key, so the size and
                         startup checks miss those subpackages.
new policy blocks / legacy warns:
    T3_ogg_audio         .ogg/.oga audio. iOS cannot decode ogg; a Douyin 3.6 case stayed on the Cocos start screen
                         until the sounds were mp3.
    T4_texture_over_4096 a PNG/JPG wider or taller than 4096 px: over the WebGL MAX_TEXTURE_SIZE of many phones, the
                         upload fails and the load stops at 100% or the game crashes.
    T5_path_chars        a whitespace, '#', '?' or '%' in a file path. TikTok's debug page: "Resource file paths don't
                         contain spaces"; '#', '?' and '%' end or change the URL the downloader requests.
warning only:
    W_texture_over_2048  a PNG/JPG side over 2048 px (old phones with a 2048 texture limit; Cocos forum "stuck at 100%").
    W_image_cache_off    game JavaScript sets cc.macro.CLEANUP_IMAGE_CACHE = false (keeps every decoded image in memory
                         after upload to the GPU; iOS memory crash case on the Cocos forum).
Already covered elsewhere and not repeated here: touch clientX/clientY (audit_upload_startup, kit touch part),
tt.getOpenDataContext sub-context (adapter_fix), WebP (webp, structure K_S_webp), 0-byte files (structure
K_S_zero_byte), path case and missing require targets (audit_upload_startup), main package 4 MB (verify_native_zip).
"""
import re
import struct

from . import finding

PROVIDER = re.compile(r'^(tt|wx)[0-9a-f]{16}$', re.I)
OGG = ('.ogg', '.oga')
IMAGES = ('.png', '.jpg', '.jpeg')
HARD_SIDE, SOFT_SIDE = 4096, 2048
PATH_CHARS = re.compile(r'[\s#?%]')
CACHE_OFF = re.compile(r'\bCLEANUP_IMAGE_CACHE\s*=\s*(?:false|!1|0)\b')
PNG_SIG = b'\x89PNG\r\n\x1a\n'
JPEG_SOF = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}


def image_size(data):
    """(width, height) of a PNG or JPEG, or None when the header cannot be read."""
    if data[:8] == PNG_SIG and len(data) >= 24 and data[12:16] == b'IHDR':
        return struct.unpack('>II', data[16:24])
    if data[:2] != b'\xff\xd8':
        return None
    i, n = 2, len(data)
    while i + 4 <= n:
        if data[i] != 0xFF:
            return None
        marker = data[i + 1]
        if marker == 0xFF:              # fill byte
            i += 1
            continue
        if marker in (0x01, 0xD8) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        if marker in (0xD9, 0xDA):      # end of image / start of scan before any frame header
            return None
        length = struct.unpack('>H', data[i + 2:i + 4])[0]
        if marker in JPEG_SOF and i + 9 <= n:
            height, width = struct.unpack('>HH', data[i + 5:i + 9])
            return width, height
        i += 2 + length
    return None


def _plugin_findings(game):
    if 'plugins' not in game:
        return []
    plugins = game['plugins']
    if not isinstance(plugins, dict):
        return [finding('T1_engine_plugin', 'block', 'game.json "plugins" is not an object; remove it and rebuild with '
                        '"separate engine" off', {'plugins': repr(plugins)[:120]})]
    out = []
    for name, spec in sorted(plugins.items()):
        spec = spec if isinstance(spec, dict) else {}
        provider = str(spec.get('provider') or '')
        version = str(spec.get('version') or '').strip()
        why = []
        if name.casefold() == 'cocos':
            why.append('plugins.cocos is the separated Cocos engine plugin')
        if PROVIDER.match(provider):
            why.append('provider %s is a Douyin/WeChat app id' % provider)
        if not version:
            why.append('no version')
        evidence = {'plugin': name, 'provider': provider, 'version': version, 'path': spec.get('path')}
        if why:
            out.append(finding('T1_engine_plugin', 'block', 'game.json plugins.%s: %s. TikTok looks plugins up by name '
                               'and version in its own library and stops with "The current game plugin version does '
                               'not exist", so the engine never loads. Rebuild with "separate engine" (分离引擎) off: '
                               'cocos/cocos2d-js-min.js goes into the package and game.json has no plugins'
                               % (name, '; '.join(why)), evidence))
        else:
            out.append(finding('T1_engine_plugin', 'warn', 'game.json plugins.%s (provider %s, version %s): TikTok '
                               'documents no plugin list; confirm it loads in TikTok DevTool and on a phone'
                               % (name, provider or '-', version), evidence))
    return out


def _subpackage_key_findings(game):
    odd = sorted(k for k in game if isinstance(k, str) and k.casefold() == 'subpackages' and k != 'subpackages')
    if not odd:
        return []
    return [finding('T2_subpackages_key', 'block', 'game.json uses %s; TikTok needs lowercase "subpackages" (@ttmg/cli '
                    'refuses other casing and the size/startup checks only read the lowercase key). Rename the key'
                    % ', '.join('"%s"' % k for k in odd), {'keys': odd})]


def _texture_findings(view, level):
    hard, soft, unreadable = [], [], []
    for name, data in sorted(view.files.items()):
        if not name.lower().endswith(IMAGES):
            continue
        size = image_size(data)
        if size is None:
            unreadable.append(name)
            continue
        side = max(size)
        if side > HARD_SIDE:
            hard.append((name, size))
        elif side > SOFT_SIDE:
            soft.append((name, size))

    def show(items):
        return ', '.join('%s %dx%d' % (n, w, h) for n, (w, h) in items[:5])

    out = []
    if hard:
        out.append(finding('T4_texture_over_4096', level, '%d image(s) over %d px on a side (%s): over the WebGL texture '
                           'limit of many phones; scale them down or split them' % (len(hard), HARD_SIDE, show(hard)),
                           [{'file': n, 'width': w, 'height': h} for n, (w, h) in hard[:20]]))
    if soft:
        out.append(finding('W_texture_over_2048', 'warn', '%d image(s) over %d px on a side (%s): fine on current '
                           'phones, may fail on old phones with a 2048 texture limit' % (len(soft), SOFT_SIDE, show(soft)),
                           [{'file': n, 'width': w, 'height': h} for n, (w, h) in soft[:20]]))
    if unreadable:
        out.append(finding('W_texture_unreadable', 'warn', '%d .png/.jpg file(s) whose size could not be read (%s): '
                           'check they are real images' % (len(unreadable), ', '.join(unreadable[:5])), unreadable[:20]))
    return out


def check(view):
    policy, _why = view.get_policy()
    level = 'block' if policy == 'new' else 'warn'
    game = view.game_json
    out = _plugin_findings(game) + _subpackage_key_findings(game)
    ogg = sorted(n for n in view.files if n.lower().endswith(OGG))
    if ogg:
        out.append(finding('T3_ogg_audio', level, '%d .ogg audio file(s) (%s): iOS cannot play ogg and a Cocos game '
                           'can stay on its start screen; convert them to mp3' % (len(ogg), ', '.join(ogg[:3])), ogg[:20]))
    out += _texture_findings(view, level)
    odd = sorted(n for n in view.files if PATH_CHARS.search(n))
    if odd:
        out.append(finding('T5_path_chars', level, '%d file path(s) with a space, #, ? or %% (%s): TikTok downloads '
                           'resources by URL and these break it; rename them' % (len(odd), ', '.join(odd[:3])), odd[:20]))
    cache = []
    for name in view.game_js():
        m = CACHE_OFF.search(view.text(name))
        if m:
            cache.append(name)
    if cache:
        out.append(finding('W_image_cache_off', 'warn', 'cc.macro.CLEANUP_IMAGE_CACHE is set to false in %s: every '
                           'decoded image stays in memory and iOS can close the game. Keep the build template value '
                           '(true) unless the game needs cc.dynamicAtlasManager; then check memory on an iPhone'
                           % ', '.join(cache[:3]), cache[:10]))
    return out
