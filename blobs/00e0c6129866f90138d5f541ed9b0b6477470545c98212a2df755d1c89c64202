"""Shared step interface for tiktok_finalize (v7.7, design D77 1.3-1.5).

Every step module in this package exposes
    detect(ctx) -> 'absent' | 'kit_current' | 'kit_old' | 'own' | 'conflict' | 'n/a'
    apply(ctx)  -> Result.as_dict(): {'changed': [{file, before_sha256, after_sha256, what}], 'blocks', 'warnings'}
    verify(view_or_files, manifest, policy) -> findings     (read only; package_gates.kit_parts reuses it)

KIT_MANIFEST.json (kit 2.0, `parts` section, optional `includes`) is the ONLY source of hashes, file names and
wiring lines; no step writes its own hash. A step that cannot be sure (anchor found 0 or 2+ times, a kit file that
differs from the manifest, a missing tool) refuses: it never guesses and never skips.
"""
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT_DIR = HERE.parent.parent / 'assets' / 'platform-kit'
MANIFEST = KIT_DIR / 'KIT_MANIFEST.json'

SOURCE_STEPS = ('images', 'kit_sources', 'physics_clock',   # physics_clock: v7.8 P16 (new 2.4 physics games)
                'build_templates', 'settings', 'orientation',   # orientation: v7.8 B31
                'art_static')        # art_static: v7.8 U7（补）squashed sprites, invisible colliders (read only, after images)
NATIVE_STEPS = ('adapter', 'touch', 'storage', 'startup', 'login', 'appid', 'png', 'structure')
POLICIES = ('new', 'legacy')
MARK = re.compile(r'//\s*tiktok-kit:([\w.-]+):([\w.-]+)')


class KitError(Exception):
    """The kit itself is not usable (manifest missing, kit file differs from its manifest hash)."""


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def finding(gate_id, level, message, evidence=None):
    out = {'id': gate_id, 'level': level, 'message': message}
    if evidence is not None:
        out['evidence'] = evidence
    return out


class Manifest:
    """KIT_MANIFEST.json with its `includes` merged (parts-3x/KIT_PARTS_3X.json from W-A2)."""

    def __init__(self, data, kit_dir):
        self.data = data
        self.kit_dir = Path(kit_dir)
        self.version = str(data.get('version', ''))
        self.files = data.get('files') or {}
        self.parts = dict(data.get('parts') or {})
        self.included = []
        for inc in data.get('includes') or []:
            path = self.kit_dir / inc
            try:
                sub = json.loads(path.read_text(encoding='utf-8'))
            except (OSError, ValueError) as error:
                raise KitError('manifest include %s unreadable: %s' % (inc, error))
            for name, part in (sub.get('parts') or {}).items():
                if name in self.parts:
                    raise KitError('part %s defined twice (KIT_MANIFEST.json and %s)' % (name, inc))
                self.parts[name] = part
            self.included.append(inc)

    def has_parts(self):
        return bool(self.parts)

    def part(self, name):
        return self.parts.get(name)

    def parts_for(self, engine, phase=None):
        out = []
        for name, part in sorted(self.parts.items()):
            if part.get('engine') not in (None, engine, 'any'):
                continue
            if phase and part.get('phase') not in (None, phase):
                continue
            out.append((name, part))
        return out

    def kit_bytes(self, name):
        """Bytes of a part's kit file, refused unless they equal the manifest sha256."""
        part = self.parts[name]
        spec = part.get('file') or {}
        src = self.kit_dir / spec.get('src', '')
        if not spec.get('src') or not src.is_file():
            raise KitError('kit file for part %s missing: %s' % (name, spec.get('src')))
        data = src.read_bytes()
        if sha256(data) != spec.get('sha256'):
            raise KitError('kit file %s differs from KIT_MANIFEST (sha %s, manifest %s)'
                           % (spec['src'], sha256(data)[:12], str(spec.get('sha256'))[:12]))
        return data

    def all_versions(self, name):
        spec = (self.parts.get(name) or {}).get('file') or {}
        return ({spec.get('sha256')} | set(spec.get('previous_sha256') or [])) - {None}

    def kit_hashes(self):
        """Every sha256 the kit has ever shipped (files + parts, current and previous): such a file is never 'own'."""
        out = {v.get('sha256') for v in self.files.values() if isinstance(v, dict)}
        for name in self.parts:
            out |= self.all_versions(name)
        return out - {None}


def load_manifest(path=None):
    path = Path(path) if path else MANIFEST
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise KitError('KIT_MANIFEST unreadable (%s): %s' % (path, error))
    return Manifest(data, path.parent)


def file_state(data, manifest, name):
    """State of one placed kit file: absent / kit_current / kit_old / own."""
    if data is None:
        return 'absent'
    spec = manifest.parts[name].get('file') or {}
    digest = sha256(data)
    if digest == spec.get('sha256'):
        return 'kit_current'
    if digest in set(spec.get('previous_sha256') or []):
        return 'kit_old'
    return 'own'


def marker(part, version):
    return '// tiktok-kit:%s:%s' % (part, version)


def kit_lines(text, part):
    """[(start, end, version)] of whole lines carrying this part's marker comment."""
    out = []
    for m in MARK.finditer(text):
        if m.group(1) != part:
            continue
        start = text.rfind('\n', 0, m.start()) + 1
        end = text.find('\n', m.end())
        out.append((start, len(text) if end < 0 else end, m.group(2)))
    return out


STATEMENT_START = re.compile(r'(?:^|[;{}\n])[ \t]*$')


def anchors(text, pattern):
    """Matches of a wiring anchor that start a statement (an anchor inside an expression is not usable)."""
    rx = re.compile(pattern)
    found = list(rx.finditer(text))
    usable = [m for m in found if STATEMENT_START.search(text[max(0, m.start() - 200):m.start()])]
    return found, usable


def wire_line(text, part, version, wiring):
    """Insert (or refresh) one marked line next to the wiring anchor.
    -> (new_text, state, detail). state: kit_current (left alone) | kit_old (line replaced) | absent (inserted) |
    conflict (refused; text unchanged)."""
    line = wiring['line']
    if marker(part, version) not in line:
        line = line.rstrip() + ' ' + marker(part, version)
    have = kit_lines(text, part)
    if len(have) > 1:
        return text, 'conflict', '%d marked %s lines' % (len(have), part)
    if have:
        start, end, ver = have[0]
        if ver == version and text[start:end].strip() == line.strip():
            return text, 'kit_current', 'line present'
        return text[:start] + line + text[end:], 'kit_old', 'line %s -> %s' % (ver, version)
    if wiring.get('insert_after'):
        pattern, after = wiring['insert_after'], True
    else:
        pattern, after = wiring.get('insert_before'), False
    if not pattern:
        return text, 'conflict', 'wiring for %s has no anchor' % part
    found, usable = anchors(text, pattern)
    if len(found) != 1 or len(usable) != 1:
        return text, 'conflict', 'anchor /%s/ found %d times (%d at a statement start); need exactly 1' % (
            pattern, len(found), len(usable))
    m = usable[0]
    line_start = text.rfind('\n', 0, m.start()) + 1
    indent = text[line_start:m.start()] if not text[line_start:m.start()].strip() else ''
    if after:
        pos = m.end()
        nl = text.find('\n', pos)
        rest = text[pos:nl if nl >= 0 else len(text)]
        if rest.strip() and not rest.strip().startswith('//'):
            # anchor not at the end of its line: put the line right after it, then continue the old line
            return text[:pos] + '\n' + indent + line + '\n' + indent + text[pos:].lstrip(' \t'), 'absent', \
                'inserted after anchor'
        pos = len(text) if nl < 0 else nl + 1
        return text[:pos] + indent + line + '\n' + text[pos:], 'absent', 'inserted after anchor'
    if indent or line_start == m.start():
        return text[:line_start] + indent + line + '\n' + text[line_start:], 'absent', 'inserted before anchor'
    return text[:m.start()] + line + '\n' + text[m.start():], 'absent', 'inserted before anchor'


def wiring_ok(text, part, version, wiring):
    """Read-only K2 check: exactly one marked line, current version, on the right side of exactly one anchor."""
    have = kit_lines(text, part)
    if len(have) != 1:
        return False, '%d marked %s lines (need 1)' % (len(have), part)
    start, end, ver = have[0]
    if ver != version:
        return False, 'marked line is kit %s, current %s' % (ver, version)
    pattern = wiring.get('insert_after') or wiring.get('insert_before')
    if not pattern:
        return True, 'line present'
    found = list(re.finditer(pattern, text))
    if len(found) != 1:
        return False, 'anchor /%s/ found %d times' % (pattern, len(found))
    if wiring.get('insert_after') and not start >= found[0].end():
        return False, 'line is before the anchor (must come after it)'
    if not wiring.get('insert_after') and not end <= found[0].start():
        return False, 'line is after the anchor (must come before it)'
    return True, 'line present, anchor order right'


class Result:
    def __init__(self, step):
        self.step = step
        self.state = None
        self.changed, self.blocks, self.warnings, self.info = [], [], [], []

    def change(self, rel, before, after, what):
        self.changed.append({'file': rel, 'before_sha256': sha256(before) if before is not None else None,
                             'after_sha256': sha256(after) if after is not None else None, 'what': what})

    def block(self, gate_id, message, evidence=None):
        self.blocks.append(finding(gate_id, 'block', message, evidence))

    def warn(self, gate_id, message, evidence=None):
        self.warnings.append(finding(gate_id, 'warn', message, evidence))

    def as_dict(self):
        return {'step': self.step, 'state': self.state, 'changed': self.changed, 'blocks': self.blocks,
                'warnings': self.warnings, 'info': self.info}


class Ctx:
    """What one finalize run works on. phase 'source' -> root is the Cocos project; 'native' -> the build folder."""

    def __init__(self, phase, root, *, project=None, board=None, engine=None, policy='new', manifest=None,
                 app_id=None, removed_dir=None, options=None):
        if policy not in POLICIES:
            raise ValueError('policy must be new or legacy, not %r' % (policy,))
        self.phase = phase
        self.root = Path(root)
        self.project = Path(project) if project else (self.root if phase == 'source' else None)
        self.board = board
        self.engine = engine
        self.policy = policy
        self.manifest = manifest
        self.app_id = app_id
        self.options = dict(options or {})
        if removed_dir:
            self.removed_dir = Path(removed_dir)
        elif phase == 'source':
            self.removed_dir = self.root / '.tiktok-kit' / 'removed'
        else:
            self.removed_dir = self.root.parent / '.tiktok-kit-removed' / self.root.name

    def path(self, rel):
        return self.root / rel

    def read(self, rel):
        p = self.path(rel)
        return p.read_bytes() if p.is_file() and not p.is_symlink() else None

    def write(self, rel, data):
        p = self.path(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def move_away(self, rel):
        """Move a file out of the build/project into removed_dir (never deleted, never inside the ZIP)."""
        src = self.path(rel)
        dest = self.removed_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            dest = dest.with_name(dest.name + '.' + sha256(src.read_bytes())[:8])
        src.replace(dest)
        return dest

    def files(self, root_only=False):
        """{relpath: bytes} of the folder (junk skipped). root_only: top-level files only."""
        out = {}
        paths = self.root.glob('*') if root_only else self.root.rglob('*')
        for p in sorted(paths):
            if p.is_file() and not p.is_symlink() and p.name not in ('.DS_Store', 'Thumbs.db') \
                    and not p.name.startswith('._') and '__MACOSX' not in p.parts:
                out[p.relative_to(self.root).as_posix()] = p.read_bytes()
        return out


# ---------------------------------------------------------------- native parts (touch, storage, startup, login)
# A manifest part names its step with "step" (touch | storage | startup | login | webp_probe); older drafts use the
# design's part names, so these aliases are accepted too. A wiring entry may carry "engine" (2 | 3).
STEP_ALIASES = {'touch': ('touch24', 'touch3x'), 'storage': ('storage', 'storage24', 'storage3x'),
                'startup': ('startup24',), 'login': ('login', 'login24', 'login3x'),
                'webp_probe': ('webp_probe24', 'webp_probe3x')}
ENGINE_JS = re.compile(r'(^|/)(cocos2d-js(-min)?(\.[0-9a-f]{5,})?|physics(-min)?|cocos-js/.*|'
                       r'src/(system|polyfills)\.bundle)\.js$', re.I)
ADAPTER_JS = re.compile(r'(^|/)(adapter(-min)?|web-adapter|engine-adapter|libs/.*adapter.*|jsb-adapter/.*)\.js$',
                        re.I)
STOCK_ROOT_JS = {'game.js', 'main.js', 'ccRequire.js', 'application.js', 'src/settings.js', 'src/import-map.js'}
MAIN_REQUIRE = re.compile(r'require\(\s*[\'"](?:\./)?main(?:\.js)?[\'"]\s*\)')


def step_parts(manifest, step, engine):
    out = []
    for name, part in manifest.parts_for(engine):
        if part.get('step') == step or (not part.get('step') and name in STEP_ALIASES.get(step, ())):
            out.append((name, part))
    return out


def wirings(part, engine, where=None):
    return [w for w in part.get('wiring') or []
            if w.get('engine') in (None, engine) and (where is None or w.get('in') == where)]


def text_of(data):
    return '' if data is None else data.decode('utf-8', 'replace')


def require_rx(dest):
    stem = dest[:-3] if dest.endswith('.js') else dest
    return re.compile(r'require\(\s*[\'"](?:\./)?%s(?:\.js)?[\'"]\s*\)' % re.escape(stem))


def line_bounds(text, pos):
    start = text.rfind('\n', 0, pos) + 1
    end = text.find('\n', pos)
    return start, len(text) if end < 0 else end


def live_matches(text, rx):
    """Matches that are not on a // comment line."""
    out = []
    for m in rx.finditer(text):
        start, _ = line_bounds(text, m.start())
        if not text[start:m.start()].lstrip().startswith('//'):
            out.append(m)
    return out


def neutralize(text, rx, tag):
    """Comment out each line that loads a module, when that line is one whole statement (balanced brackets).
    -> (new_text, done_count, refused_lines). Refused lines (e.g. a require that opens a callback wrapping the
    engine) stay; the caller decides whether that blocks."""
    done, refused, out = 0, [], text
    for m in reversed(live_matches(text, rx)):
        start, end = line_bounds(out, m.start())
        line = out[start:end]
        balanced = all(line.count(a) == line.count(b) for a, b in ('()', '{}', '[]'))
        bound = re.search(r'(?:\b(?:var|let|const|return)\b[^;]*|[\w$\]).]\s*=(?![=>])[^;]*)$', line[:m.start() - start])
        if not balanced or bound or line.count('require(') != 1:
            refused.append(line.strip()[:160])
            continue
        indent = line[:len(line) - len(line.lstrip())]
        out = out[:start] + indent + '// tiktok-kit-removed:%s: ' % tag + line.strip() + out[end:]
        done += 1
    return out, done, refused


def is_engine_or_adapter(rel):
    return bool(ENGINE_JS.search(rel) or ADAPTER_JS.search(rel))


def kit_main_versions(manifest):
    out = set()
    spec = manifest.files.get('build-templates/bytedance/main.js')
    if isinstance(spec, dict) and spec.get('sha256'):
        out.add(spec['sha256'])
    for name, _ in step_parts(manifest, 'startup', 2):
        out |= manifest.all_versions(name)
    return out


def kit_main_current(manifest):
    for name, part in step_parts(manifest, 'startup', 2):
        return (part.get('file') or {}).get('sha256')
    spec = manifest.files.get('build-templates/bytedance/main.js')
    return spec.get('sha256') if isinstance(spec, dict) else None


def own_layers(files, manifest, part, scope='all'):
    """[(relpath, hits)] of JavaScript that is an own layer of this part and no kit file: its path matches the part's
    own_files, or its text matches own_markers. Paths matching own_skip, the engine and the adapter never count.
    scope 'root' = top-level files only (what finalize can move); 'all' = every JS file."""
    pats = [re.compile(p) for p in part.get('own_markers') or []]
    names = [re.compile(p) for p in part.get('own_files') or []]
    skip = [re.compile(p) for p in part.get('own_skip') or []]
    if not pats and not names:
        return []
    kit = manifest.kit_hashes()
    out = []
    for rel, data in sorted(files.items()):
        if not rel.endswith('.js') or is_engine_or_adapter(rel) or (scope == 'root' and '/' in rel) \
                or any(s.search(rel) for s in skip):
            continue
        if sha256(data) in kit:
            continue
        text = text_of(data)
        if rel == 'game.js':
            # the kit's marked lines, comment lines (incl. tiktok-kit-removed) and load lines are no own layer
            text = '\n'.join(l for l in text.split('\n') if not l.lstrip().startswith('//')
                             and not MARK.search(l) and 'require(' not in l)
        hits = ['file:' + p.pattern for p in names if p.search(rel)] + [p.pattern for p in pats if p.search(text)]
        if hits:
            out.append((rel, hits))
    return out


ACTIONS = {'replace': 'replace', 'install': 'replace', 'restore': 'replace', 'add_if_absent': 'add_if_absent',
           'none': 'skip', 'skip': 'skip', 'warn': 'skip', 'report': 'skip',
           'install_only_with_exception': 'exception'}


def part_action(part, policy, default):
    raw = (part.get('policy') or {}).get(policy) or default
    return ACTIONS.get(raw, 'skip' if policy == 'legacy' else 'replace')


def part_facts(files, manifest, name, part, engine):
    """Read-only facts about one native part in a build {relpath: bytes}."""
    spec = part.get('file') or {}
    dest = spec.get('dest')
    data = files.get(dest) if dest else None
    game = text_of(files.get('game.js'))
    main = text_of(files.get('main.js'))
    main_is_kit = files.get('main.js') is not None and sha256(files['main.js']) in kit_main_versions(manifest)
    via_main = bool(main_is_kit and any(w.get('kit_line') and w['kit_line'] in main
                                        for w in wirings(part, engine, 'main.js')))
    marked = kit_lines(game, name)
    rx = require_rx(dest) if dest else None
    plain = [m for m in live_matches(game, rx) if not any(s <= m.start() < e for s, e, _ in marked)] if rx else []
    return {'dest': dest, 'state': file_state(data, manifest, name) if dest else 'n/a', 'via_main': via_main,
            'main_is_kit': main_is_kit, 'marked': marked, 'plain': plain, 'game': game,
            'game_requires_main': bool(live_matches(game, MAIN_REQUIRE)),
            'own': [o for o in own_layers(files, manifest, part) if o[0] != dest]}


def _order_ok(text, pos_start, pos_end, wiring):
    pattern = wiring.get('insert_after') or wiring.get('insert_before')
    if not pattern:
        return True, 'no anchor'
    found = list(re.finditer(pattern, text))
    if len(found) != 1:
        return False, 'anchor /%s/ found %d times' % (pattern, len(found))
    if wiring.get('insert_after'):
        return (pos_start >= found[0].end(), 'load line must come after /%s/' % pattern)
    return (pos_end <= found[0].start(), 'load line must come before /%s/' % pattern)


def part_findings(files, manifest, name, part, engine, policy, required=True):
    """K1/K2/K3 findings for one native part (shared by the steps' self-check and package_gates.kit_parts)."""
    out = []
    f = part_facts(files, manifest, name, part, engine)
    ours = bool(f['marked'])
    strict = policy == 'new'
    level = 'block' if strict else 'warn'
    if not strict and not ours:
        for rel, hits in f['own']:
            out.append(finding('K3_single_layer', 'warn', 'legacy game keeps its own %s layer in %s (%s)'
                               % (name, rel, ', '.join(hits)), {'part': name, 'file': rel}))
        return out
    if not required and f['state'] == 'absent' and not ours and not f['plain']:
        return out
    if f['state'] != 'kit_current':
        lvl = 'warn' if (not strict and f['state'] == 'kit_old') else 'block'
        out.append(finding('K1_kit_bytes', lvl, '%s: %s is %s (manifest sha %s)' % (
            name, f['dest'], {'absent': 'missing', 'kit_old': 'an older kit version', 'own': 'not the kit file'}
            .get(f['state'], f['state']), str((part.get('file') or {}).get('sha256'))[:12]),
            {'part': name, 'file': f['dest'], 'state': f['state']}))
    game_w = wirings(part, engine, 'game.js')
    if f['via_main']:
        if not f['game_requires_main']:
            out.append(finding('K2_kit_wiring', 'block', '%s is loaded by the kit main.js, but game.js never '
                               "requires './main' (template present, never loaded: Nanas)" % name, {'part': name}))
        if f['marked'] or f['plain']:
            out.append(finding('K2_kit_wiring', 'block', '%s is loaded twice: kit main.js and %d line(s) in game.js'
                               % (name, len(f['marked']) + len(f['plain'])), {'part': name}))
    else:
        total = len(f['marked']) + len(f['plain'])
        if total != 1:
            out.append(finding('K2_kit_wiring', 'block', '%s: game.js loads %s %d times (need exactly 1)'
                               % (name, f['dest'], total), {'part': name, 'count': total}))
        elif f['marked']:
            ok, why = wiring_ok(f['game'], name, manifest.version, game_w[0]) if game_w else (False, 'no wiring')
            if not ok:
                out.append(finding('K2_kit_wiring', 'block', '%s: %s' % (name, why), {'part': name}))
        elif game_w:
            m = f['plain'][0]
            ok, why = _order_ok(f['game'], m.start(), m.end(), game_w[0])
            if not ok:
                out.append(finding('K2_kit_wiring', 'block', '%s: %s' % (name, why), {'part': name}))
    for rel, hits in f['own']:
        out.append(finding('K3_single_layer', level, 'second %s layer in %s (%s)' % (name, rel, ', '.join(hits)),
                           {'part': name, 'file': rel}))
    return out


def install_part(ctx, r, name, part, action):
    """Install / refresh one native part in ctx.root (a build folder). action: replace | add_if_absent | skip."""
    engine = ctx.engine
    files = ctx.files()
    f = part_facts(files, ctx.manifest, name, part, engine)
    r.state = f['state'] if not f['own'] else ('own' if f['state'] in ('absent', 'own') else f['state'])
    if action == 'skip':
        r.info.append('%s not installed (%s policy)' % (name, ctx.policy))
        return
    try:
        kit = ctx.manifest.kit_bytes(name)
    except KitError as error:
        r.block('K_kit_unusable', str(error))
        return
    dest = f['dest']
    if action == 'add_if_absent' and not f['marked']:
        if f['own'] or f['plain'] or f['via_main'] or f['state'] != 'absent':
            for rel, hits in f['own']:
                r.warn('K_W_own_' + name, 'legacy game keeps its own %s layer in %s (%s); hand it to this game\'s '
                       'session' % (name, rel, ', '.join(hits)), {'file': rel})
            if f['state'] in ('own', 'kit_old'):
                r.warn('K_W_own_' + name, 'legacy game keeps its %s %s (%s, not the current kit file)'
                       % (name, dest, f['state']), {'file': dest, 'state': f['state']})
            r.info.append('%s left as is (legacy game, already has a layer)' % name)
            return
    game = f['game']
    if action == 'replace':
        for rel, hits in f['own']:
            if rel == 'game.js' or '/' in rel:
                r.block('K3_single_layer', 'own %s layer inside %s (%s) cannot be removed automatically; remove it '
                        'in the project and rebuild' % (name, rel, ', '.join(hits)), {'file': rel})
                continue
            game, done, refused = neutralize(game, require_rx(rel), name)
            if refused:
                r.block('K3_single_layer', 'own %s layer %s is loaded by a line finalize cannot take out: %s'
                        % (name, rel, refused[0]), {'file': rel})
                continue
            moved = ctx.move_away(rel)
            r.change(rel, files[rel], None, 'own %s layer moved to %s' % (name, moved))
        if r.blocks:
            return
    if f['state'] != 'kit_current':
        if files.get(dest) is not None:
            ctx.move_away(dest)
        ctx.write(dest, kit)
        r.change(dest, files.get(dest), kit, 'kit %s %s' % (name, 'installed' if f['state'] == 'absent'
                                                            else 'replaced (%s)' % f['state']))
    if f['via_main']:
        if f['marked'] or f['plain']:
            game, _, refused = neutralize(game, require_rx(dest), name + '-double')
            if refused:
                r.block('K2_kit_wiring', '%s loaded by kit main.js and again by game.js: %s' % (name, refused[0]))
    elif len(f['plain']) == 1 and not f['marked']:
        r.info.append('%s already loaded by game.js (unmarked line kept)' % name)
    elif len(f['plain']) > 1:
        r.block('K2_kit_wiring', 'game.js loads %s %d times' % (dest, len(f['plain'])))
    else:
        game_w = wirings(part, engine, 'game.js')
        if not game_w:
            r.block('K2_kit_wiring', 'KIT_MANIFEST part %s has no game.js wiring for engine %s' % (name, engine))
        else:
            game, state, detail = wire_line(game, name, ctx.manifest.version, game_w[0])
            if state == 'conflict':
                r.block('K2_kit_wiring', 'game.js: %s' % detail, {'part': name})
    old = files.get('game.js')
    if game != text_of(old) and not r.blocks:
        ctx.write('game.js', game.encode('utf-8'))
        r.change('game.js', old, game.encode('utf-8'), '%s load line' % name)


def self_check(ctx, r, names_parts, policy, required=True):
    """Re-read the build and run the gate checks on what was just written; any block refuses the package."""
    files = ctx.files()
    for name, part in names_parts:
        for item in part_findings(files, ctx.manifest, name, part, ctx.engine, policy, required):
            if item['level'] == 'block' and not any(b['message'] == item['message'] for b in r.blocks):
                r.blocks.append(dict(item, message='after install: ' + item['message']))


def run_part_step(ctx, step, defaults, label):
    """apply() body shared by the native steps that place one kit file + one load line (touch, storage)."""
    r = Result(step)
    if ctx.engine not in (2, 3):
        (r.block if ctx.policy == 'new' else r.warn)('K_engine_unknown', 'not a Cocos 2.4 / 3.x mini-game build; '
                                                     '%s not installed' % label)
        r.state = 'n/a'
        return r.as_dict()
    parts = step_parts(ctx.manifest, step, ctx.engine)
    actions = [(n, p, part_action(p, ctx.policy, defaults[ctx.policy])) for n, p in parts]
    actions = [(n, p, 'skip' if a == 'exception' and not ctx.options.get('keep_webp_exception') else
                ('replace' if a == 'exception' else a)) for n, p, a in actions]
    if not parts:
        if defaults[ctx.policy] != 'skip':
            (r.block if ctx.policy == 'new' else r.warn)(
                'K1_kit_bytes', 'KIT_MANIFEST has no %s part for Cocos %s' % (label, '2.4' if ctx.engine == 2 else '3.x'))
        r.state = 'n/a'
        return r.as_dict()
    for name, part, action in actions:
        install_part(ctx, r, name, part, action)
    if not r.blocks:
        self_check(ctx, r, [(n, p) for n, p, a in actions if a != 'skip'], ctx.policy,
                   required=ctx.policy == 'new')
    return r.as_dict()


def part_step_detect(ctx, step):
    parts = step_parts(ctx.manifest, step, ctx.engine) if ctx.engine in (2, 3) else []
    if not parts:
        return 'n/a'
    files = ctx.files()
    states = []
    for name, part in parts:
        f = part_facts(files, ctx.manifest, name, part, ctx.engine)
        if f['own']:
            states.append('own')
        elif f['state'] == 'kit_old' or (f['marked'] and f['marked'][0][2] != ctx.manifest.version):
            states.append('kit_old')
        elif f['state'] == 'kit_current' and (f['via_main'] or len(f['marked']) + len(f['plain']) == 1):
            states.append('kit_current')
        else:
            states.append(f['state'] if f['state'] != 'kit_current' else 'absent')
    for s in ('conflict', 'own', 'kit_old', 'absent'):
        if s in states:
            return s
    return 'kit_current'


def part_step_verify(files, manifest, policy, step, engine=None):
    from .policy import engine_of_names
    engine = engine or engine_of_names(files)
    out = []
    for name, part in step_parts(manifest, step, engine) if engine in (2, 3) else []:
        out += part_findings(files, manifest, name, part, engine, policy, required=policy == 'new')
    return out
