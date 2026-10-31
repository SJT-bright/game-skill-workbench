"""Shared TikTok package gates (v7.5, v7.7): ONE function every package entry calls.

make_tiktok_zip.native_problems() (both writers: make_tiktok_zip.py and build_checked_zip.py) and
check_package.check() call run() on the exact bytes that go into the ZIP, so no entry can skip a gate.
A gate never depends on what the game declares about itself; it reads the package.

Contract (stable; gate modules plug in without changing callers):
    run(files, root=None, board=None, *, policy=None, context=None) -> {
        'blocks':   [finding, ...],   # any entry here refuses the package
        'warnings': [finding, ...],   # reported, never refuse
        'gates':    [module names that ran],
        'missing':  [module names not present in this tree],
        'engine_major': 2 | 3 | None,
        'policy': 'new' | 'legacy', 'policy_reason': str,
    }
    run(..., modules=('network',)) restricts the run to some modules (calibration and unit tests only;
    every package entry calls run() without it).
    finding = {'id': 'G1_growth_apis', 'level': 'block' | 'warn', 'message': str, 'evidence': optional}

v7.7 (design D77 1.5, 2): PackageView.policy is 'new' | 'legacy'. A writer passes the policy of its finalize record
(policy=record['policy']) so gates and finalize agree; without it the policy is judged from the package itself
(tiktok_finalize_steps.policy.decide(files=...): scene / asset uuids against LEGACY_GAMES.json, not listed = new).
check_package.py given only a ZIP therefore judges the policy from the artifact. context = writer-only view
attributes for kit_parts K4/K5: {'writer': True, 'finalize_record': record, 'project': path,
'finalize_options': {...}}. There is no argument that makes a package legacy against the list.

Gate modules live next to this file. Each exposes check(view) -> list of findings. A module listed in
GATE_MODULES that fails to import or raises is itself a block (a broken gate never passes silently).
"""
import importlib
import json
import re
from pathlib import Path

GATE_MODULES = ('network', 'mission', 'startup', 'webp', 'ads_static', 'adapter_fix', 'kit_parts')
POLICIES = ('new', 'legacy')
CONTEXT_KEYS = ('writer', 'finalize_record', 'project', 'finalize_options')

ENGINE = re.compile(r'(^|/)(cocos2d-js(-min)?|physics(-min)?|cocos-js/.*|src/system\.bundle|polyfills\.bundle|'
                    r'src/polyfills\.bundle)\.js$', re.I)
ADAPTER = re.compile(r'(^|/)(adapter(-min)?|web-adapter|engine-adapter|libs/.*adapter.*|jsb-adapter/.*)\.js$', re.I)


class PackageView:
    """Read-only view of one Native (mini-game) build: {posix relpath: bytes}."""

    def __init__(self, files, root=None, board=None, policy=None, context=None):
        self.files = dict(files)
        self.root = Path(root) if root else None
        self.board = board            # 'remake' | 'localize' | None (unknown)
        if policy is not None and policy not in POLICIES:
            raise ValueError('policy must be new or legacy, not %r' % (policy,))
        self.policy = policy          # 'new' | 'legacy' | None (judged from the package on first use)
        self._policy_decision = None
        for key, value in (context or {}).items():
            if key not in CONTEXT_KEYS:
                raise ValueError('unknown package gate context %r' % key)
            setattr(self, key, value)
        self._text = {}
        try:
            game = json.loads(self.files.get('game.json', b'{}').decode('utf-8-sig'))
        except (ValueError, UnicodeDecodeError):
            game = {}
        self.game_json = game if isinstance(game, dict) else {}
        subs = self.game_json.get('subpackages') or []
        self.subpackages = []
        for sub in subs if isinstance(subs, list) else []:
            if isinstance(sub, dict) and isinstance(sub.get('root'), str):
                self.subpackages.append({'root': sub['root'].strip().strip('/') + '/',
                                         'name': sub.get('name') or sub['root'].strip().strip('/'),
                                         'independent': sub.get('independent') is True})
        names = list(self.files)
        if any(re.search(r'(^|/)cocos2d-js(-min)?\.js$', n) for n in names):
            self.engine_major = 2
        elif any(n.startswith('cocos-js/') or re.search(r'(^|/)web-adapter\.js$', n) for n in names):
            self.engine_major = 3
        else:
            self.engine_major = None

    def get_policy(self):
        """-> (policy, reason). The caller's policy when given, else the policy of the writer's finalize record
        (context finalize_record), else judged from the package bytes once (fail closed: unreadable = 'new')."""
        if self.policy in POLICIES:
            return self.policy, 'given by the caller'
        record = getattr(self, 'finalize_record', None)
        if isinstance(record, dict) and record.get('policy') in POLICIES:
            # a writer view always judges by THIS run's finalize record (an init-marked new game whose scene
            # uuids are on the legacy list stays new: W-D4 request 3)
            return record['policy'], "from this run's finalize record"
        if self._policy_decision is None:
            try:
                import sys as _sys
                scripts = str(Path(__file__).resolve().parent.parent)
                if scripts not in _sys.path:
                    _sys.path.insert(0, scripts)
                from tiktok_finalize_steps import policy as _P
                out = _P.decide(files=self.files)
                self._policy_decision = (out['policy'], 'judged from the package: ' + out['reason'])
            except Exception as error:  # noqa: BLE001 - never let a broken decision make a game legacy
                self._policy_decision = ('new', 'policy decision failed (%r) -> new game' % (error,))
        return self._policy_decision

    def text(self, name):
        if name not in self._text:
            self._text[name] = self.files[name].decode('utf-8', 'replace')
        return self._text[name]

    def is_engine(self, name):
        return bool(ENGINE.search(name))

    def is_adapter(self, name):
        return bool(ADAPTER.search(name))

    def subpackage_of(self, name):
        for sub in self.subpackages:
            if name.startswith(sub['root']):
                return sub
        return None

    def main_files(self):
        return [n for n in self.files if self.subpackage_of(n) is None]

    def js(self):
        return sorted(n for n in self.files if n.lower().endswith('.js'))

    def game_js(self):
        """JavaScript that is neither the engine nor the platform adapter."""
        return [n for n in self.js() if not self.is_engine(n) and not self.is_adapter(n)]


def finding(gate_id, level, message, evidence=None):
    out = {'id': gate_id, 'level': level, 'message': message}
    if evidence is not None:
        out['evidence'] = evidence
    return out


def run(files, root=None, board=None, *, modules=None, policy=None, context=None):
    view = PackageView(files, root, board, policy, context)
    blocks, warnings, ran, missing = [], [], [], []
    for name in GATE_MODULES if modules is None else tuple(modules):
        full = __name__ + '.' + name
        try:
            module = importlib.import_module(full)
        except ModuleNotFoundError as error:
            if error.name == full:
                missing.append(name)
                continue          # not written yet (development only; release requires every module)
            blocks.append(finding('GATE_LOAD_' + name, 'block', 'gate module %s failed to import: %s' % (name, error)))
            continue
        except Exception as error:  # noqa: BLE001 - a broken gate must refuse, never pass
            blocks.append(finding('GATE_LOAD_' + name, 'block', 'gate module %s failed to import: %r' % (name, error)))
            continue
        check = getattr(module, 'check', None)
        if check is None:
            continue              # helper module without a static check (for example adapter_fix.apply only)
        try:
            found = check(view) or []
        except Exception as error:  # noqa: BLE001
            blocks.append(finding('GATE_ERROR_' + name, 'block', 'gate %s raised: %r' % (name, error)))
            continue
        for item in found:
            (blocks if item.get('level') == 'block' else warnings).append(item)
        ran.append(name)
    for name in missing:      # v7.7.4 (总表 B18): a missing gate never passes silently
        blocks.append(finding('GATE_MISSING_' + name, 'block', 'gate module package_gates/%s.py is missing from this '
                              'Skill install, so its checks did not run; reinstall the Skill' % name))
    policy_now, policy_reason = view.get_policy()
    return {'blocks': blocks, 'warnings': warnings, 'gates': ran, 'missing': missing,
            'engine_major': view.engine_major, 'board': board, 'policy': policy_now, 'policy_reason': policy_reason}


def messages(findings):
    return ['%s: %s' % (f['id'], f['message']) for f in findings]


def summary(result):
    """Compact form for writer/check reports: ids and messages, evidence trimmed to 5 entries."""
    def trim(f):
        out = dict(f)
        if isinstance(out.get('evidence'), list):
            out['evidence'] = out['evidence'][:5]
        return out
    return {'blocks': [trim(f) for f in result['blocks']], 'warnings': [trim(f) for f in result['warnings']],
            'gates': result['gates'], 'missing': result.get('missing', []),
            'engine_major': result.get('engine_major'), 'board': result.get('board'),
            'policy': result.get('policy'), 'policy_reason': result.get('policy_reason')}


def run_dir(native, board=None, modules=None, policy=None, context=None):
    """Convenience for tests and calibration: read a Native build folder (junk files skipped)."""
    native = Path(native)
    files = {}
    for path in sorted(native.rglob('*')):
        if path.is_file() and not path.is_symlink() and path.name not in ('.DS_Store', 'Thumbs.db') \
                and not path.name.startswith('._') and '__MACOSX' not in path.parts:
            files[path.relative_to(native).as_posix()] = path.read_bytes()
    return run(files, native, board, modules=modules, policy=policy, context=context)


if __name__ == '__main__':
    import sys
    result = run_dir(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(1 if result['blocks'] else 0)
