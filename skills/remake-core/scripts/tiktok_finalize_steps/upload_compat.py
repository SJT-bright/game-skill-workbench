"""Native step: TikTok upload compatibility (11.17.15, the fix that let 鸽鸽小羊 pass upload). Both policies.

Saul 2026-11-08 ("请参照小羊已上传成功的修复方式"): three files are normalised in the build folder, everything else keeps
its bytes. The game's subpackages, engine start structure, App ID and other settings stay as they are; reference
files are never copied over.

  game.json            every subpackage root that names a real folder gets its trailing "/"
                       ("subpackages/resources" -> "subpackages/resources/"; subpackages and subPackages both)
  game.js              every require('<local file>') that resolves to a file in the build becomes "./<path>.<ext>"
                       with the real extension ("adapter-min.js" -> "./adapter-min.js", "./main" -> "./main.js",
                       "./src/settings" -> "./src/settings.js"); unresolved names are reported, never guessed
  project.config.json  setting.es6 = false, setting.minified = true, setting.urlCheck = true; the old
                       setting.postcss and newFeature (setting or top level) are removed. Cocos 3.x: es6 is only
                       reported (no 3.x upload has proved es6 false yet); the other three changes apply.

The kit's own game.js anchors already accept "./main.js" and "./adapter-min.js" (KIT_MANIFEST wirings), so this step
runs last and changes nothing the earlier steps verify. A second run changes nothing (state kit_current).
Calibrated on 鸽鸽小羊 (the uploaded package, 英文成品/最新交付): a stock Cocos 2.4 game.js / game.json /
project.config.json is turned into exactly its game.js and game.json and the same project.config.json settings.
"""
import json
import posixpath
import re

from . import Result, text_of

STEP = 'upload_compat'
SETTING_WANT = (('es6', False), ('minified', True), ('urlCheck', True))
SETTING_DROP = ('postcss', 'newFeature')
REQUIRE = re.compile(r'''(\brequire\s*\(\s*)(['"])([^'"\n]+)\2''')
EXTENSIONS = ('.js', '.json')


def _resolve(spec, names):
    """-> './path.ext' for a local file in the build, or None. Package names and absolute paths are left alone."""
    if spec.startswith('/') or '://' in spec:
        return None
    rel = posixpath.normpath(spec[2:] if spec.startswith('./') else spec)
    if rel.startswith('../') or rel == '..':
        return None
    for candidate in (rel,) + tuple(rel + ext for ext in EXTENSIONS):
        if candidate in names and candidate.endswith(EXTENSIONS):
            return './' + candidate
    return None


def game_js_changes(text, names):
    """-> (new_text, [(old, new)], [unresolved]) for root game.js."""
    pairs, unresolved = [], []

    def fix(m):
        line = text[text.rfind('\n', 0, m.start()) + 1:m.start()]
        if '//' in line or line.lstrip().startswith('*'):
            return m.group(0)                      # commented out (a removed startup file): not a live reference
        spec = m.group(3)
        want = _resolve(spec, names)
        if want is None:
            local = spec.startswith('.') or '/' in spec or spec.endswith(EXTENSIONS)
            if local and not spec.startswith('/') and '://' not in spec:
                unresolved.append(spec)
            return m.group(0)
        if want != spec:
            pairs.append((spec, want))
        return m.group(1) + m.group(2) + want + m.group(2)

    return REQUIRE.sub(fix, text), pairs, unresolved


def game_json_changes(text, folders):
    """-> (new_text, [root fixed]) keeping the file's bytes apart from the roots."""
    try:
        data = json.loads(text)
    except ValueError:
        return None, []
    subs = []
    for key in ('subpackages', 'subPackages'):
        if isinstance(data.get(key), list):
            subs += [s for s in data[key] if isinstance(s, dict) and isinstance(s.get('root'), str)]
    fixed = []
    for sub in subs:
        root = sub['root']
        if not root or root.endswith('/') or posixpath.normpath(root) not in folders:
            continue
        rx = re.compile(r'("root"\s*:\s*")' + re.escape(root) + r'"')
        text, n = rx.subn(lambda m: m.group(1) + root + '/"', text, count=1)
        if n:
            fixed.append(root)
    return text, fixed


def _indent(text):
    """Keep the file's own indentation (Cocos writes 4 spaces, some templates 2)."""
    m = re.search(r'\n([ \t]+)\S', text)
    if not m:
        return 2
    return m.group(1) if '\t' in m.group(1) else len(m.group(1))


def project_config_changes(text, engine):
    """-> (new_text or None, [what], [warnings])."""
    try:
        data = json.loads(text)
    except ValueError:
        return None, [], ['project.config.json is not JSON']
    if not isinstance(data, dict):
        return None, [], ['project.config.json is not an object']
    what, warn = [], []
    setting = data.get('setting')
    if not isinstance(setting, dict):
        setting = {}
    for key, value in SETTING_WANT:
        if key == 'es6' and engine == 3:
            if setting.get('es6') is not False:
                warn.append('Cocos 3.x: setting.es6 is %r; left as built (no 3.x upload has proved es6 false yet)'
                            % (setting.get('es6'),))
            continue
        if setting.get(key) is not value:
            what.append('setting.%s %r -> %r' % (key, setting.get(key), value))
            setting[key] = value
    for key in SETTING_DROP:
        if key in setting:
            what.append('removed setting.%s' % key)
            del setting[key]
        if key in data:
            what.append('removed %s' % key)
            del data[key]
    if not what:
        return None, [], warn
    data['setting'] = setting
    return json.dumps(data, ensure_ascii=False, indent=_indent(text)) + '\n', what, warn


def folders_of(names):
    out = set()
    for name in names:
        d = posixpath.dirname(name)
        while d and d not in out:
            out.add(d)
            d = posixpath.dirname(d)
    return out


def verify(files, engine=None):
    """Read-only: what this step would still change in these files (empty = compatible)."""
    out = []
    names = set(files)
    folders = folders_of(names)
    if 'game.json' in files:
        _, fixed = game_json_changes(text_of(files['game.json']), folders)
        out += ['game.json root %s needs a trailing /' % r for r in fixed]
    if 'game.js' in files:
        _, pairs, _ = game_js_changes(text_of(files['game.js']), names)
        out += ['game.js require %s -> %s' % p for p in pairs]
    if 'project.config.json' in files:
        _, what, _ = project_config_changes(text_of(files['project.config.json']), engine)
        out += ['project.config.json ' + w for w in what]
    return out


def detect(ctx):
    return 'kit_current' if not verify(ctx.files(), ctx.engine) else 'absent'


def apply(ctx):
    r = Result(STEP)
    files = ctx.files()
    names = set(files)
    folders = folders_of(names)
    changed = False

    raw = files.get('game.json')
    if raw is not None:
        new, fixed = game_json_changes(text_of(raw), folders)
        if new is None:
            r.warn('K_W_upload_compat_game_json', 'game.json is not JSON; subpackage roots not checked')
        elif fixed:
            data = new.encode('utf-8')
            ctx.write('game.json', data)
            r.change('game.json', raw, data, 'subpackage root trailing / : %s' % ', '.join(fixed))
            changed = True

    raw = files.get('game.js')
    if raw is not None:
        new, pairs, unresolved = game_js_changes(text_of(raw), names)
        if pairs:
            data = new.encode('utf-8')
            ctx.write('game.js', data)
            r.change('game.js', raw, data, 'local requires: ' + '; '.join('%s -> %s' % p for p in pairs))
            changed = True
        if unresolved:
            r.warn('K_W_upload_compat_require', 'game.js requires a local path that is not in the build: %s'
                   % ', '.join(sorted(set(unresolved))[:6]), sorted(set(unresolved)))

    raw = files.get('project.config.json')
    if raw is not None:
        new, what, warn = project_config_changes(text_of(raw), ctx.engine)
        for w in warn:
            r.warn('K_W_upload_compat_config', w)
        if new is not None:
            data = new.encode('utf-8')
            ctx.write('project.config.json', data)
            r.change('project.config.json', raw, data, '; '.join(what))
            changed = True

    left = verify(ctx.files(), ctx.engine)
    for item in left:
        r.block('K_upload_compat', 'after write: ' + item)
    r.state = 'own' if changed else 'kit_current'
    r.info.append('upload compat: %s' % ('changed ' + ', '.join(c['file'] for c in r.changed) if changed
                                         else 'already compatible'))
    return r.as_dict()
