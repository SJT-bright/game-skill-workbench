"""Content-bound reuse for platform preparation; never a replacement for final ZIP checks.

Source/sync share audited per-step input scopes. Successful mutators are recorded against
their resulting state, not their old inputs, so reuse cannot skip a required modification.
Unknown steps, missing tools, symbolic links and failed results execute normally and are
not cached. Original results and execution timestamps remain immutable evidence.
"""
import ast
import copy
import hashlib
import inspect
import json
import os
import shutil
import stat
import sys
import tempfile
import time
import threading
from contextlib import contextmanager
from functools import wraps
from datetime import datetime, timezone
from pathlib import Path
from contextvars import ContextVar

SCHEMA = 'preparation-cache.v1'
HOME = Path('.tiktok-kit/preparation-cache')
HERE = Path(__file__).resolve().parent
SKIP = {'library', 'temp', 'build', 'local', 'node_modules', '.git', '__pycache__', '__MACOSX'}
CODE = ('.js', '.ts')
SCENE = ('.scene', '.fire', '.prefab')
PURE = {'frame_scan', 'ui_kit_scan', 'home_entry_scan', 'save_read_scan', 'plugin3x_scan',
        'game_name_scan', 'skin_preview_scan', 'slot_overlap_scan', 'reward_order_scan',
        'debug_leftover_scan', 'art_static', 'orientation'}
SOURCE = PURE | {'images', 'kit_sources', 'physics_clock', 'build_templates', 'startup',
                 'settings', 'capsule_auto', 'bg_cover', 'ui_kit', 'run_parts'}
NATIVE = {'adapter', 'startup', 'touch', 'storage', 'rewarded', 'login', 'appid', 'png', 'structure'}
_HASH_MEMO = ContextVar('preparation_hash_memo', default=None)
_LOCKS, _LOCK_GUARD, _LOCK_DEPTH = {}, threading.Lock(), threading.local()


@contextmanager
def project_lock(project):
    """One preparation owner per project, across threads/processes; nested calls reuse ownership."""
    if not project:
        yield
        return
    key = str(Path(project).resolve())
    with _LOCK_GUARD:
        lock = _LOCKS.setdefault(key, threading.RLock())
    with lock:
        depths = getattr(_LOCK_DEPTH, 'depths', {})
        if depths.get(key):
            depths[key] += 1
            try:
                yield
            finally:
                depths[key] -= 1
            return
        # Ownership must not mutate a legacy/report-only project. Keep the tiny lock
        # outside the game; successful evidence itself remains inside its project.
        path = Path(tempfile.gettempdir()) / 'cocos-preparation-locks' / (digest(key) + '.lock')
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a+b') as stream:
            if os.name == 'nt':
                import msvcrt
                if path.stat().st_size == 0:
                    stream.write(b'0')
                    stream.flush()
                stream.seek(0)
                while True:
                    try:
                        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                        break
                    except OSError:
                        time.sleep(0.05)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            depths[key] = 1
            _LOCK_DEPTH.depths = depths
            try:
                yield
            finally:
                depths.pop(key, None)
                if os.name == 'nt':
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def serialized(fn):
    """Protect the entire mutating pipeline, not just a single hash read."""
    signature = inspect.signature(fn)
    @wraps(fn)
    def wrapped(*args, **kwargs):
        arguments = signature.bind_partial(*args, **kwargs).arguments
        started = time.monotonic()
        with project_lock(arguments.get('project')):
            acquired = time.monotonic()
            result = fn(*args, **kwargs)
        if isinstance(result, dict):
            result['preparation_runtime'] = {'elapsed_seconds': time.monotonic() - started,
                                             'lock_wait_seconds': acquired - started}
        return result
    return wrapped


class Uncacheable(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), default=str)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def stamp():
    return datetime.now(timezone.utc).isoformat()


def file_identity(path):
    path = Path(path)
    try:
        before = path.lstat()
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(before.st_mode):
        raise Uncacheable('symbolic-link dependency: ' + str(path))
    if stat.S_ISDIR(before.st_mode):
        return {'directory': True}
    if not stat.S_ISREG(before.st_mode):
        raise Uncacheable('non-regular dependency: ' + str(path))
    signature = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns, before.st_mode)
    memo = _HASH_MEMO.get()
    key = str(path.absolute())
    if memo is not None and key in memo and memo[key][0] == signature:
        return memo[key][1]
    result = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'executable': os.access(path, os.X_OK)}
    after = path.stat()
    if signature != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns, after.st_mode):
        raise Uncacheable('dependency changed while fingerprinting: ' + str(path))
    if memo is not None:
        memo[key] = (signature, result)
    return result


def walk(root, *, prune=True):
    root = Path(root)
    if not root.exists():
        return
    if root.is_symlink():
        raise Uncacheable('symbolic-link root: ' + str(root))
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if not (prune and (d in SKIP or d == '.tiktok-kit')))
        for name in dirs:
            if (Path(base) / name).is_symlink():
                raise Uncacheable('symbolic-link directory: ' + str(Path(base) / name))
        for name in sorted(files):
            if prune and (name in ('.DS_Store', 'Thumbs.db') or name.startswith('._')):
                continue
            yield Path(base) / name


def tree(root, selector=lambda rel: True, *, prune=True):
    root = Path(root)
    return {p.relative_to(root).as_posix(): file_identity(p) for p in walk(root, prune=prune)
            if selector(p.relative_to(root).as_posix())}


def explicit(root, paths):
    return {rel: file_identity(Path(root) / rel) for rel in paths}


def project_inputs(ctx, name):
    """Scopes match readers in the registered steps; listing names detects additions/removals."""
    root = Path(ctx.project or ctx.root)
    names = {name} if isinstance(name, str) else set(name)
    def selected_one(rel, name):
        suffix = Path(rel).suffix.lower()
        asset = rel.startswith('assets/')
        if name in {'frame_scan', 'home_entry_scan', 'reward_order_scan', 'physics_clock'}:
            return asset and suffix in CODE
        if name == 'save_read_scan':
            return asset and suffix in CODE or rel in {
                'assets/resources/config/level_plan.json', 'docs/levels/level_plan.json',
                'docs/levels/level_resources.json'}
        if name in {'ui_kit_scan', 'capsule_auto', 'bg_cover'}:
            return asset and (suffix in CODE + SCENE or suffix == '.meta') or rel == 'docs/art/static-exempt.json'
        if name in {'kit_sources', 'ui_kit', 'run_parts'}:
            # Manifest-defined destinations need not end in .js.
            return asset and (suffix in CODE or suffix == '.meta' or rel.startswith('assets/tiktok-platform/'))
        if name == 'plugin3x_scan':
            return asset and (suffix in CODE or suffix == '.meta') or rel == 'docs/platform/platform_ids.json'
        if name == 'slot_overlap_scan':
            return asset and suffix in SCENE or rel == 'docs/art/bind_log.json'
        if name == 'skin_preview_scan':
            return Path(rel).name in {'skins.json', 'unlock_table.json'} or asset and suffix in CODE
        if name == 'debug_leftover_scan':
            return asset and (suffix in CODE + SCENE or suffix == '.meta') or rel.startswith('settings/') or rel == 'docs/copy/glossary.json'
        if name == 'orientation':
            return asset and suffix in SCENE or rel.startswith('settings/')
        if name in {'build_templates', 'startup'}:
            return rel.startswith('build-templates/')
        if name == 'settings':
            return rel.startswith(('settings/', 'profiles/', 'assets/tiktok-platform/'))
        if name == 'art_static':
            return asset and (suffix in SCENE + ('.meta', '.png', '.jpg', '.jpeg', '.webp')) or rel.startswith('settings/') or rel == 'docs/art/static-exempt.json'
        if name == 'game_name_scan':
            return (suffix in SCENE or rel in {'project.config.json', 'package.json',
                    'docs/copy/glossary.json', 'docs/copy/copy-table.csv',
                    'docs/english/chinese-audit/audit.json'} or
                    rel.startswith('build-templates/') and Path(rel).name == 'project.config.json' or
                    rel.startswith('docs/') and Path(rel).name in {'receipt.json', 'result.json'})
        # Images and complete Native preparation depend on source references, metadata,
        # source pixels, settings and the explicit overrides below.
        return rel.startswith(('assets/', 'settings/', 'profiles/', 'build-templates/'))
    found = tree(root, lambda rel: any(selected_one(rel, name) for name in names))
    found.update(explicit(root, ('project.json', 'package.json', 'project.config.json',
                                '.tiktok-kit/policy.json', '.tiktok-kit/image-overrides.json')))
    if names & {'images', '@native'}:
        try:
            overrides = json.loads((root / '.tiktok-kit/image-overrides.json').read_text()).get('images', {})
            refs = []
            for raw in overrides:
                key = str(raw).replace('\\', '/').lstrip('./')
                stem = key.rsplit('.', 1)[0] if '.' in key.rsplit('/', 1)[-1] else key
                for candidate in [key] + [stem + '.' + ext for ext in ('png', 'jpg', 'jpeg', 'webp')]:
                    refs.extend((candidate, candidate + '.meta'))
            found['@override_sources'] = explicit(root, sorted(set(refs)))
        except (OSError, ValueError, AttributeError, TypeError):
            pass  # The override bytes themselves remain bound; the real step validates them.
    if 'game_name_scan' in names:
        # Historical OCR receipts can name files outside the project; preserve that
        # dependency as data too instead of trusting the receipt's claimed hash.
        refs = []
        for p in (root / 'docs').rglob('receipt.json') if (root / 'docs').is_dir() else []:
            try:
                row = json.loads(p.read_text())
            except (ValueError, OSError):
                continue
            image = row.get('image_path') if isinstance(row, dict) else None
            if image:
                img = Path(str(image))
                refs.extend((str(img if img.is_absolute() else root / img), str(root / 'assets' / img.name)))
        audit = root / 'docs/english/chinese-audit/audit.json'
        try:
            data = json.loads(audit.read_text())
            for row in data.get('items', []) if isinstance(data, dict) else []:
                if isinstance(row, dict) and row.get('file'):
                    refs.append(str((root / str(row['file'])).resolve()))
        except (ValueError, OSError):
            pass
        found['@external_images'] = {r: file_identity(r) for r in sorted(set(refs))}
        found['@folder_names'] = [root.name, root.parent.name]
    if 'plugin3x_scan' in names:
        from tiktok_finalize_steps.plugin3x_scan import peers_of
        peers = {}
        for peer in peers_of(ctx):
            peer = peer.resolve()
            matches = set()
            for prefix in ('', '*/', '*/*/', '*/*/*/'):
                matches.update(peer.glob(prefix + 'assets/tiktok-platform/PlatformConfig*.js'))
            peers[str(peer)] = {str(p): file_identity(p) for p in sorted(matches)}
        found['@peers'] = peers
    return found


def python_dependencies(paths):
    """Local static import closure, including function-local imports and package initializers.

    Dynamic platform-kit imports are bound by the kit tree below. The finalizer's
    orchestration file is hashed separately so unrelated reporting/timer imports do
    not accidentally become scanner rules.
    """
    roots = (HERE, HERE.parents[1] / 'cocos-game-check/package-check/scripts')
    todo, found = list(paths), {}

    def resolve(base, module):
        p = base.joinpath(*module.split('.')) if module else base
        for candidate in (p.with_suffix('.py'), p / '__init__.py'):
            if candidate.is_file():
                todo.append(candidate)

    while todo:
        path = Path(todo.pop()).resolve()
        if str(path) in found or not path.is_file():
            continue
        found[str(path)] = file_identity(path)
        memo = _HASH_MEMO.get()
        key = ('imports', str(path), found[str(path)]['sha256'])
        module = memo.get(key) if memo is not None else None
        if module is None:
            module = ast.parse(path.read_bytes(), filename=str(path))
            if memo is not None:
                memo[key] = module
        for node in ast.walk(module):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for base in roots:
                        resolve(base, alias.name)
            elif isinstance(node, ast.ImportFrom):
                bases = (path.parent.parents[node.level - 2],) if node.level > 1 else \
                    (path.parent,) if node.level == 1 else roots
                for base in bases:
                    resolve(base, node.module or '')
                    for alias in node.names:
                        if alias.name != '*':
                            resolve(base, '.'.join(x for x in (node.module, alias.name) if x))
    return found


def tool_inputs(ctx, names=()):
    paths = [HERE / 'tiktok_finalize_steps' / (name + '.py') for name in names]
    paths += [HERE / 'tiktok_finalize_steps/__init__.py', HERE / 'tiktok_finalize_steps/policy.py']
    tools = python_dependencies(paths)
    for path in (HERE / 'preparation_cache.py', HERE / 'tiktok_finalize.py'):
        tools[str(path)] = file_identity(path)
    # Python may write bytecode while importing check_kit_project. It is generated
    # cache, not a new rule; bind the actual .py and kit resources instead. This
    # exclusion applies only to tools, never to the deliverable Native tree.
    kit = tree(ctx.manifest.kit_dir,
               lambda r: '__pycache__' not in Path(r).parts and not r.endswith(('.pyc', '.pyo')),
               prune=False) if ctx.manifest else {}
    return {'tools': digest(tools), 'kit': digest(kit),
            'manifest': digest({'data': ctx.manifest.data, 'parts': ctx.manifest.parts}) if ctx.manifest else None,
            'python': sys.version}


def runtime_inputs(ctx, names):
    out = {}
    if 'settings' in names or 'appid' in names:
        path = Path(ctx.options.get('ad_config') or Path.home() / '.game-skill/ad-config.json')
        out['ad_config'] = {'path': str(path.resolve()), 'identity': file_identity(path)}
    if 'images' in names or 'art_static' in names or 'png' in names:
        try:
            import PIL
            out['Pillow'] = PIL.__version__
        except ImportError:
            out['Pillow'] = None
    if 'png' in names:
        from tiktok_finalize_steps import png
        exe = png.pngquant_path(ctx)
        if not exe or not os.access(exe, os.X_OK):
            raise Uncacheable('pngquant unavailable')
        resolved = shutil.which(str(exe)) or str(exe)
        out['pngquant'] = {'path': str(Path(resolved).resolve()), 'identity': file_identity(resolved),
                           'version': png.pngquant_version(resolved), 'args': png.ARGS}
        path = png._cache_path(ctx)
        out['png_cache'] = file_identity(path) if path else None
    return out


def context(ctx):
    # png_cache_read_only changes cache writes, not prepared output bytes. Other
    # options, even unknown ones, remain part of the contract.
    options = {k: v for k, v in ctx.options.items() if k != 'png_cache_read_only'}
    # Source receipts spell out the empty WebP reason; CLI callers omit it. They
    # mean the same preparation contract, so do not create a false cache miss.
    options['keep_webp_exception'] = str(options.get('keep_webp_exception') or '').strip()
    options = json.loads(canonical(options))
    return {'phase': ctx.phase, 'engine': ctx.engine, 'board': ctx.board, 'policy': ctx.policy,
            'policy_override': bool(getattr(ctx, 'preparation_policy_override', False)),
            'app_id': str(ctx.app_id) if ctx.app_id is not None else None, 'options': options}


def read_record(path, binding):
    try:
        row = json.loads(path.read_text())
        if row.get('schema') != SCHEMA or row.get('binding') != binding or row.get('result_sha256') != digest(row['result']):
            return None
        if row['result'].get('blocks') or row['result'].get('state') == 'error':
            return None
        return row
    except (OSError, ValueError, KeyError, TypeError):
        return None


def write_record(path, binding, result, started, seconds):
    if result.get('blocks') or result.get('state') == 'error':
        return None
    row = {'schema': SCHEMA, 'binding': binding, 'result': result, 'result_sha256': digest(result),
           'executed_at': started, 'seconds': seconds}
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.preparation-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(canonical(row) + '\n')
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return row


def reused_result(row, path):
    result = copy.deepcopy(row['result'])
    result['changed'] = []
    result['preparation'] = {'reused': True, 'executed_at': row['executed_at'],
                             'original_seconds': row['seconds'], 'seconds': 0.0,
                             'evidence': str(path), 'binding_sha256': digest(row['binding'])}
    if row.get('requested_prepared_png_only'):
        result['preparation']['requested_prepared_png_only'] = True
        result['preparation']['proof_mode'] = 'exact full preparation satisfies prepared-only request'
    for step in result.get('steps', []):
        step['changed'] = []
        step['preparation'] = dict(result['preparation'])
    return result


class Session:
    def __init__(self, ctx):
        self.ctx = ctx
        self.home = Path(ctx.project) / HOME if ctx.project else None
        # Hash bytes once per invocation; every access still checks inode/size/mtime/ctime
        # and every directory is re-enumerated. Nothing stat-only persists across runs.
        self.hash_memo = {}

    def binding(self, name):
        if self.ctx.phase != 'source' or self.ctx.policy != 'new' or name not in SOURCE or self.home is None:
            raise Uncacheable('unknown preparation scope')
        token = _HASH_MEMO.set(self.hash_memo)
        try:
            return {'scope': name, 'context': context(self.ctx), 'inputs': project_inputs(self.ctx, name),
                    'tools': tool_inputs(self.ctx, (name,)), 'runtime': runtime_inputs(self.ctx, (name,))}
        finally:
            _HASH_MEMO.reset(token)

    def lookup(self, name):
        binding = self.binding(name)
        path = self.home / ('source-' + name) / (digest(binding) + '.json')
        return binding, path, read_record(path, binding)

    def apply(self, name, fn):
        started = time.monotonic()
        with project_lock(self.ctx.project):
            acquired = time.monotonic()
            result = self._apply_locked(name, fn)
        if isinstance(result.get('preparation'), dict):
            elapsed = time.monotonic() - started
            prep = result['preparation']
            prep.update(elapsed_seconds=elapsed, lock_wait_seconds=acquired - started,
                        binding_seconds=max(0.0, elapsed - (acquired - started) - prep.get('seconds', 0.0)))
        return result

    def _apply_locked(self, name, fn):
        try:
            before, path, row = self.lookup(name)
        except Exception:  # A broken optional cache must fall back to the real step.
            return fn()
        if row:
            # Editors do not share our ownership lock. Rebind after reading a hit so
            # a change in that read window cannot attach old evidence to new inputs.
            try:
                confirmed = self.binding(name)
            except Exception:
                return fn()
            if confirmed == before:
                return reused_result(row, path)
            before = confirmed
        started, tick = stamp(), time.monotonic()
        result = fn()
        elapsed = time.monotonic() - tick
        try:
            after = self.binding(name)
            if not valid_step_transition(before, after, result, pure=name in PURE):
                result.setdefault('blocks', []).append({'id': 'K_preparation_input_changed', 'level': 'block',
                    'message': name + ': inputs or rules changed outside this step\'s reported writes; result not reusable'})
            if not result.get('blocks') and result.get('state') != 'error':
                path = self.home / ('source-' + name) / (digest(after) + '.json')
                write_record(path, after, result, started, elapsed)
                result['preparation'] = {'reused': False, 'executed_at': started, 'seconds': elapsed,
                                         'evidence': str(path), 'binding_sha256': digest(after)}
        except Exception as error:
            result.setdefault('info', []).append('Preparation reuse not recorded: ' + str(error))
        return result


def valid_step_transition(before, after, result, *, pure=False):
    if pure:
        return before == after
    # Only writes reported by this mutator may explain changed project inputs.
    # An external file or tool changed after being read is never endorsed as tested.
    if any(before.get(k) != after.get(k) for k in ('scope', 'context', 'tools', 'runtime')):
        return False
    writes = {c.get('file'): c.get('after_sha256') for c in result.get('changed', []) if isinstance(c, dict)}
    prior, current = before['inputs'], after['inputs']
    for key in set(prior) | set(current):
        if prior.get(key) == current.get(key):
            continue
        if key == '@override_sources':
            old_refs, new_refs = prior.get(key, {}), current.get(key, {})
            for rel in set(old_refs) | set(new_refs):
                if old_refs.get(rel) != new_refs.get(rel) and not _matches_write(rel, new_refs.get(rel), writes):
                    return False
        elif not _matches_write(key, current.get(key), writes):
            return False
    return True


def _matches_write(rel, identity, writes):
    return rel in writes and (identity.get('sha256') if isinstance(identity, dict) else None) == writes[rel]


def source_pipeline_binding(ctx, names, session=None):
    """Identity of an executed pipeline's final state, not a claim its early steps reran.

    Later mutators can legitimately change an earlier step's dependencies. The overall
    receipt binds the observed final state; per-step cache entries keep their own true
    execution state and are never silently moved to that final state.
    """
    if set(names) - SOURCE or ctx.policy != 'new':
        raise Uncacheable('unknown source pipeline')
    session = session or Session(ctx)
    token = _HASH_MEMO.set(session.hash_memo)
    try:
        # Union the audited dependencies once. This is the same dependency contract
        # as per-step reuse, without re-reading every shared file for every step.
        return digest({'steps': list(names), 'context': context(ctx), 'inputs': project_inputs(ctx, names),
                       'tools': tool_inputs(ctx, names), 'runtime': runtime_inputs(ctx, names)})
    finally:
        _HASH_MEMO.reset(token)


def native_binding(ctx, names):
    names = tuple(names)
    if not ctx.project or ctx.policy != 'new' or not names or set(names) - NATIVE:
        raise Uncacheable('no project or unknown Native preparation step')
    return {'scope': 'native', 'steps': list(names), 'context': context(ctx),
            'native': tree(ctx.root, prune=False), 'project': project_inputs(ctx, '@native'),
            'tools': tool_inputs(ctx, names), 'runtime': runtime_inputs(ctx, names)}


def native_lookup(ctx, names):
    try:
        binding = native_binding(ctx, names)
        path = Path(ctx.project) / HOME / 'native' / (digest(binding) + '.json')
        row = read_record(path, binding)
        if row and native_binding(ctx, names) != binding:
            return None, None
        if not row and ctx.options.get('prepared_png_only') is True:
            # A read-only writer may consume the exact successful full preparation.
            # The reverse is deliberately disallowed; every other condition remains
            # identical, including tool bytes, PNG output cache and actual Native.
            complete = copy.copy(ctx)
            complete.options = dict(ctx.options)
            complete.options.pop('prepared_png_only')
            row, path = native_lookup(complete, names)
            if row:
                row = dict(row, requested_prepared_png_only=True)
        return row, path
    except Exception:
        return None, None


def native_guard(ctx, names):
    """Inputs a Native mutator is not allowed to change (PNG cache is its own output)."""
    if not ctx.project or ctx.policy != 'new':
        raise Uncacheable('no cacheable project')
    runtime = runtime_inputs(ctx, names)
    runtime.pop('png_cache', None)
    return {'context': context(ctx), 'project': project_inputs(ctx, '@native'),
            'tools': tool_inputs(ctx, names), 'runtime': runtime, 'native': tree(ctx.root, prune=False)}


def native_store(ctx, names, result, started, seconds, guard=None):
    if result.get('blocks'):
        return
    try:
        if guard is None:
            return  # No trustworthy before snapshot: execute normally, but do not endorse a cache row.
        current_guard = native_guard(ctx, names)
        stable = all(guard.get(k) == current_guard.get(k) for k in ('context', 'project', 'tools', 'runtime'))
        writes = {c.get('file'): c.get('after_sha256') for s in result.get('steps', [])
                  for c in s.get('changed', []) if isinstance(c, dict)}
        old_native, new_native = guard['native'], current_guard['native']
        stable = stable and all(old_native.get(rel) == new_native.get(rel) or
                                _matches_write(rel, new_native.get(rel), writes)
                                for rel in set(old_native) | set(new_native))
        if not stable:
            result.setdefault('blocks', []).append({'id': 'K_preparation_input_changed', 'level': 'block',
                'message': 'Native preparation inputs or rules changed outside its reported writes'})
            return
        binding = native_binding(ctx, names)
        path = Path(ctx.project) / HOME / 'native' / (digest(binding) + '.json')
        write_record(path, binding, result, started, seconds)
        result['preparation'] = {'reused': False, 'executed_at': started, 'seconds': seconds,
                                 'evidence': str(path), 'binding_sha256': digest(binding)}
    except Exception as error:
        result.setdefault('warnings', []).append({'id': 'K_W_preparation_cache', 'level': 'warn',
                                                 'message': 'Preparation reuse not recorded: ' + str(error)})
