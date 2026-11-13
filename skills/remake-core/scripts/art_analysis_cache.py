"""Memoize only deterministic pixel analysis; never capture validity or final acceptance.

The shared checker computes results itself. Cache failure is a miss. Every hit binds
raw pixels, raw node data, project assets, policies, checker bytes and runtime.
"""
import hashlib
import hmac
import secrets
import json
import os
from pathlib import Path
import platform
import tempfile
import time


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False, default=str).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_hash(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError('symlink dependency')
    return sha(path.read_bytes())


def _owning_report(path):
    """Only known checker outputs are not policy inputs; unknown files stay bound.

    Explicit evidence references are still hashed recursively by key(). This
    prevents a saved/copied first-piece output from invalidating its own inputs.
    """
    if path.suffix.lower() != '.json':
        return False
    try:
        row = json.loads(path.read_text())
        return isinstance(row, dict) and (row.get('tool') in {
            'art_production_preflight', 'art_check', 'art_input_preflight'}
            or row.get('schema') == 'art_iteration_plan.v1')
    except (OSError, ValueError):
        return False


def snapshot(root, names, *, skip_owning_reports=False):
    result = {}
    for name in names:
        base = root / name
        if base.is_symlink():
            raise ValueError('symlink dependency')
        if not base.exists():
            result[name] = None
            continue
        paths = sorted(base.rglob('*')) if base.is_dir() else [base]
        for path in paths:
            if '__pycache__' in path.parts:
                continue
            if path.is_symlink():
                raise ValueError('symlink dependency')
            if path.is_file():
                if skip_owning_reports and path.is_relative_to(root/'docs/art') and _owning_report(path):
                    continue
                result[path.relative_to(root).as_posix()] = file_hash(path)
    return result


def tool_snapshot(root):
    return snapshot(root, [p.name for p in root.iterdir()
                          if p.is_file() and p.suffix in {'.py', '.json', '.js', '.mjs'}
                          and not p.name.startswith(('test_', 'fixture_'))])


def option_state(arguments):
    """Include optional local policy flags without depending on one installed variant."""
    result = {}
    for name, value in vars(arguments).items():
        if name in {'out', 'dumps', 'no_analysis_cache'}:
            continue
        if isinstance(value, Path):
            result[name] = {'path': str(value.resolve()),
                            'sha256': file_hash(value) if value.is_file() else None}
        else:
            result[name] = value
    return result


class PageCache:
    def __init__(self, project, options=None, enabled=True):
        self.project = Path(project).resolve()
        self.root = self.project / '.tiktok-kit/art-analysis-cache/v1'
        self.hits = self.misses = 0
        self.reason = ''
        self.base = None
        self.options = options
        self.pending = {}
        self.excluded = set()
        self.observed = {}
        if not enabled:
            self.reason = 'disabled'
            return
        try:
            import PIL
            try:
                import numpy
                numpy_version = numpy.__version__
            except ImportError:
                numpy_version = None
            # Loading can reference arbitrary build files; its existing validator always runs.
            loading = self.project / 'docs/art/official-loading.json'
            if loading.exists():
                for row in json.loads(loading.read_text())['frames']:
                    self.excluded.add(str((self.project/row['dump']).resolve()))
            from audit_glyph_core import parse_fnt
            for font in (self.project/'assets').rglob('*.fnt'):
                parsed = parse_fnt(font)
                if parsed:
                    for name in parsed['pages'].values():
                        page = (font.parent/name).resolve()
                        if not page.is_relative_to(self.project/'assets') or not page.is_file():
                            raise ValueError('external or missing bitmap page: '+str(page))
            here = Path(__file__).resolve().parent
            project_files = snapshot(self.project, [
                'assets', 'settings', 'profiles', 'extensions', 'package.json', 'project.json',
                'docs/art', 'docs/text', 'docs/art-style.txt', 'docs/features.json',
                'docs/league', 'docs/levels', 'docs/english/pre-english-images.json',
                'docs/board.txt', '.tiktok-kit/finalize-source.json', '.tiktok-kit/policy.json'],
                skip_owning_reports=True)
            tools = tool_snapshot(here)
            self.base = sha(encoded(dict(project=str(self.project), files=project_files,
                tools=tools, options=options, python=platform.python_version(),
                pillow=PIL.__version__, numpy=numpy_version)))
        except (OSError, ValueError, TypeError, KeyError) as exc:
            self.reason = str(exc)

    def key(self, document, shot):
        if self.base is None or document.get('purpose') in {'loading', 'loading_retry'} or document.get('official_loading'):
            return None
        try:
            origin = Path(document['_file']).resolve()
            if str(origin) in self.excluded:
                return None
            # Embedded observations are part of the document. Also bind every explicitly
            # referenced file and JSON attachment recursively; unresolved paths are misses.
            pending = [origin, Path(shot)]
            seen = {}
            def refs(obj, parent, location=()):
                if isinstance(obj, dict):
                    for field, value in obj.items():
                        yield from refs(value, parent, location + (field,))
                elif isinstance(obj, list):
                    for index, value in enumerate(obj):
                        yield from refs(value, parent, location + (index,))
                elif isinstance(obj, str) and Path(obj).suffix.lower() in {
                        '.png', '.jpg', '.jpeg', '.webp', '.json', '.fnt', '.ttf', '.otf', '.webm', '.mp4'}:
                    p = Path(obj)
                    # Cocos SpriteFrame.name is an identifier, even when the atlas
                    # retained a .png suffix. It is not an attachment path. The raw
                    # identifier stays in the document hash; all assets stay in base.
                    if (len(location) == 5 and location[0] == 'nodes'
                            and isinstance(location[1], int)
                            and location[2:] == ('comps', 'sprite', 'frame')
                            and p.name == obj and '/' not in obj and '\\' not in obj):
                        return
                    if not p.is_absolute():
                        candidates = [parent/p, self.project/p]
                        found = [c for c in candidates if c.is_file()]
                        if not found:
                            raise ValueError('unresolved evidence reference: ' + obj)
                        # Hash both when relative resolution is ambiguous.
                        yield from found
                    else:
                        yield p
            pending.extend(refs(document, origin.parent))
            while pending:
                p = pending.pop()
                if p.is_symlink():
                    raise ValueError('symbolic evidence link')
                p = p.resolve()
                name = str(p)
                if len(seen) > 10000:
                    raise ValueError('too many evidence dependencies')
                if name in seen:
                    continue
                seen[name] = file_hash(p)
                if p.suffix.lower() == '.json':
                    pending.extend(refs(json.loads(p.read_text()), p.parent))
            key = sha(encoded(dict(base=self.base, document=document, dependencies=seen)))
            self.observed[str(origin)] = (document, shot, key)
            return key
        except (OSError, ValueError, TypeError, KeyError) as exc:
            self.reason = str(exc)
            return None

    def _secret(self):
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root/'local-key'
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, 'wb') as f:
                f.write(secrets.token_bytes(32))
        data = path.read_bytes()
        if len(data) != 32:
            raise ValueError('invalid local cache key')
        return data

    def seal(self, key, value):
        return hmac.new(self._secret(), encoded([key, value]), hashlib.sha256).hexdigest()

    def get(self, key):
        if key is not None:
            try:
                row = json.loads((self.root/(key+'.json')).read_text())
                value = row['value']
                if (row['key'] == key and hmac.compare_digest(row['seal'], self.seal(key, value))
                        and isinstance(value, list) and len(value) == 2
                        and isinstance(value[0], list) and all(isinstance(v, str) for v in value[0])
                        and isinstance(value[1], dict)):
                    self.hits += 1
                    return value
            except (OSError, ValueError, TypeError, KeyError):
                pass
        self.misses += 1
        return None

    def put(self, key, value):
        if key is not None:
            self.pending[key] = value

    def finish(self):
        if self.base is not None:
            fresh = PageCache(self.project, self.options)
            if fresh.base != self.base:
                self.pending.clear()
                raise ValueError('art inputs changed during analysis; rerun on stable inputs')
        for document, shot, original in list(self.observed.values()):
            if self.key(document, shot) != original:
                self.pending.clear()
                raise ValueError('capture evidence changed during analysis; rerun on stable inputs')
        for key, value in self.pending.items():
            self._write(key, value)
        self.pending.clear()

    def _write(self, key, value):
        temp = None
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            data = encoded(dict(key=key, value=value, seal=self.seal(key, value)))
            with tempfile.NamedTemporaryFile(dir=self.root, delete=False) as f:
                temp = Path(f.name)
                f.write(data)
            os.replace(temp, self.root/(key+'.json'))
        except (OSError, ValueError, TypeError):
            pass
        finally:
            if temp is not None:
                temp.unlink(missing_ok=True)

    def report(self):
        return dict(reused=self.hits, recomputed=self.misses, unavailable=self.reason,
                    scope='pixel-analysis-only; capture identity and final acceptance always rechecked')
