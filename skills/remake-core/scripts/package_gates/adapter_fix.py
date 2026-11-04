"""Cocos 2.4.x ByteDance adapter auto-fix (v7.5, W1a).

The stock 2.4 adapter has three startup assumptions that hang a TikTok build on the loading page:
  sdk_version   Number.parseInt(X.SDKVersion[0])<2        throws when SystemInfo has no SDKVersion and reads "10.x"
                                                           as 1 (MusicSlice v29b, MergeShot2048 v83, DoubleJumpDuo).
  sub_context   X.isSubContext = (tt.getOpenDataContext is undefined)
                                                           the main game is taken for an open-data sub-context when
                                                           the runtime lacks getOpenDataContext (BadHairDay, RainyDuck).
  pkg_fs_access the download "doNothing" handler fs.access-probes in-package files; on a real iPhone the probe never
                                                           answered for subpackage images (MergeShot2048 v81, D6 item 2).
Completed games ship the old forms (package_scan.md: 11/20 and 7/20), so a static refusal would block good
packages. Instead both writers (make_tiktok_zip.main, build_checked_zip.build) call apply() on the Native folder
BEFORE any check: every old form must match exactly once and is rewritten; an already-fixed form is left alone;
neither form found means an adapter version this tool does not know -> block, confirm manually.
check(view) (run by package_gates in every entry, including the read-only check_package) only WARNS.

v7.7 (W-F1a): the Cocos 2.4.4 adapter has neither the SDKVersion test nor the fs.access probe (DotsDelivery v40);
its Label module without the test and its pass-through in-package handler count as the fixed form.

The SDK test is the split('.') form already used by duo_sdk_ui_retry_contract.FIXED_SDK_TEST (missing field = 2).
MusicSlice v30's String(X.SDKVersion||"2")[0] still reads "10.x" as 1, so it counts as an old form and is rewritten.
"""
import re
from pathlib import Path

from . import finding

ADAPTER_NAMES = ('adapter-min.js', 'adapter.js')
VERSION = re.compile(r'(?:ENGINE_VERSION|engineVersion)\s*=\s*["\'](\d+\.\d+\.\d+)["\']')
ENGINE_FILES = re.compile(r'^(cocos/)?cocos2d-js(-min)?(\.[0-9a-f]{5,})?\.js$')

V = r'([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)'
SDK_OLD = [re.compile(r'Number\.parseInt\(\s*' + V + r'\.SDKVersion\s*\[\s*0\s*\]\s*\)\s*<\s*2'),
           re.compile(r'Number\.parseInt\(\s*String\(\s*' + V + r'\.SDKVersion\s*\|\|\s*["\']2["\']\s*\)\s*\[\s*0\s*\]\s*\)'
                      r'\s*<\s*2')]
SDK_FIXED = re.compile(r'SDKVersion[^;\n]{0,60}\.split\(\s*["\']\.["\']\s*\)\s*\[\s*0\s*\]')
SDK_NEW = '("string"==typeof {v}.SDKVersion&&Number.parseInt({v}.SDKVersion.split(".")[0],10)<2)'

SUB_OLD = [re.compile(V + r'\.isSubContext\s*=\s*void 0\s*===\s*tt\.getOpenDataContext\b(?!\s*\()'),
           re.compile(V + r'\.isSubContext\s*=\s*tt\.getOpenDataContext\s*===\s*(?:undefined|void 0)')]
SUB_FIXED = re.compile(r'isSubContext\s*=\s*["\']function["\']\s*!==\s*typeof\s+tt\.createCanvas')
SUB_NEW = '{v}.isSubContext="function"!==typeof tt.createCanvas&&"function"===typeof tt.getSharedCanvas'

# function N(t,e,n){c(t,function(e){e?n(null,t):n(new Error("file ".concat(t," does not exist!")))})}
# function doNothing(content, options, onComplete) {\n  exists(content, function (existence) {\n    if (existence) ...
FS_HEAD = re.compile(r'function\s+([A-Za-z_$][\w$]*)\s*\(\s*([A-Za-z_$][\w$]*)\s*,\s*([A-Za-z_$][\w$]*)\s*,\s*'
                     r'([A-Za-z_$][\w$]*)\s*\)\s*\{')
FS_GUARD = ('if(!/^https?:\\/\\//.test({p})&&String({p}).indexOf((window.fsUtils&&window.fsUtils.getUserDataPath?'
            'window.fsUtils.getUserDataPath():tt.env&&tt.env.USER_DATA_PATH)||"")!==0){{{cb}(null,{p});return;}}')

# Cocos 2.4.4 adapter (v7.7 W-F1a, DotsDelivery v40): it never had the two bugs, so it counts as the fixed form.
#   sdk_version   the Label module sets the canvas pool and has no SDKVersion test at all (2.4.6+ added
#                 Number.parseInt(u.SDKVersion[0])<2 right after it). Both conditions are needed: an adapter
#                 with no SDKVersion test and no such Label module stays 'unknown'.
#   pkg_fs_access the in-package download handler only passes the path on - function A(e,t,n){n(null,e)} used as
#                 S(e,A,t,t.onFileProgress,n) - and the "does not exist!" probe is nowhere in the file.
LABEL_POOL_24_4 = re.compile(r'Object\.assign\(\s*[\w$]+\._canvasPool\s*,\s*\{\s*get\s*:\s*function\s*\(\s*\)\s*\{\s*'
                             r'return\s+[\w$]+\s*;?\s*\}\s*,\s*put\s*:\s*function\s*\(\s*\)\s*\{\s*\}\s*\}\s*\)')
PASS_24_4 = re.compile(r'function\s+([A-Za-z_$][\w$]*)\s*\(\s*([A-Za-z_$][\w$]*)\s*,\s*[A-Za-z_$][\w$]*\s*,\s*'
                       r'([A-Za-z_$][\w$]*)\s*\)\s*\{\s*\3\s*\(\s*null\s*,\s*\2\s*\)\s*;?\s*\}')


def _sdk_absent_24_4(text):
    return 'SDKVersion' not in text and bool(LABEL_POOL_24_4.search(text))


def _fs_passthrough_24_4(text):
    if 'does not exist!' in text:
        return False
    for m in PASS_24_4.finditer(text):
        use = re.compile(r'[A-Za-z_$][\w$]*\(\s*[A-Za-z_$][\w$]*\s*,\s*' + re.escape(m.group(1)) +
                         r'\s*,\s*([A-Za-z_$][\w$]*)\s*,\s*\1\.onFileProgress\s*,')
        if use.search(text):
            return True
    return False


def _engine_version(files):
    for name, data in files.items():
        if ENGINE_FILES.match(name):
            text = data.decode('utf-8', 'replace') if isinstance(data, bytes) else data
            m = VERSION.search(text)
            if m:
                return m.group(1)
    return None


def target(files):
    """(adapter names, reason): the root adapter files when this is a Cocos 2.4.x ByteDance build, else ([], why)."""
    if not all(n in files for n in ('game.js', 'game.json', 'project.config.json')):
        return [], 'not a Native mini-game build'
    version = _engine_version(files)
    if not version or not version.startswith('2.4.'):
        return [], 'not Cocos 2.4.x (engine version %s)' % (version or 'unknown')
    adapters = [n for n in ADAPTER_NAMES if n in files]
    if not adapters:
        return [], 'no root adapter file'
    text = {n: (files[n].decode('utf-8', 'replace') if isinstance(files[n], bytes) else files[n]) for n in adapters}
    adapters = [n for n in adapters if 'tt.' in text[n]]
    if not adapters:
        return [], 'adapter is not the ByteDance (tt) adapter'
    return adapters, version


def _fs_sites(text):
    """[(kind, start, end, params)] for the in-package probe handler: kind 'old' (probes) or 'fixed' (guarded)."""
    sites = []
    for head in FS_HEAD.finditer(text):
        p, cb = head.group(2), head.group(4)
        body = text[head.end():head.end() + 1200]
        if 'does not exist!' not in body[:1000]:
            continue
        probe = re.match(r'\s*([A-Za-z_$][\w$]*)\s*\(\s*' + re.escape(p) + r'\s*,\s*function', body)
        if probe:
            P, CB = re.escape(p), re.escape(cb)
            exist = re.compile(r'\s*' + re.escape(probe.group(1)) + r'\s*\(\s*' + P + r'\s*,\s*function\s*\(\s*'
                               r'([A-Za-z_$][\w$]*)\s*\)\s*\{\s*(?:if\s*\(\s*\1\s*\)\s*\{\s*' + CB + r'\s*\(\s*null\s*,\s*' + P +
                               r'\s*\)|\1\s*\?\s*' + CB + r'\s*\(\s*null\s*,\s*' + P + r'\s*\))')
            if exist.match(body):
                sites.append(('old', head.end(), head.end(), p, cb))
                continue
        cut = body.find('does not exist!')
        prefix = body[:cut]
        if FS_HEAD.search(prefix):
            continue              # the message belongs to a later named function, not this one
        if re.search(r'https\?', prefix) and re.search(r'getUserDataPath|USER_DATA_PATH', prefix) and 'return' in prefix:
            sites.append(('fixed', head.end(), head.end(), p, cb))
    return sites


def _scan(text):
    """{rule: {'old': [match objects / sites], 'fixed': bool}} for one adapter text."""
    sdk_old = [m for rx in SDK_OLD for m in rx.finditer(text)]
    sub_old = [m for rx in SUB_OLD for m in rx.finditer(text)]
    fs = _fs_sites(text)
    return {'sdk_version': {'old': sdk_old, 'fixed': bool(SDK_FIXED.search(text)) or _sdk_absent_24_4(text)},
            'sub_context': {'old': sub_old, 'fixed': bool(SUB_FIXED.search(text))},
            'pkg_fs_access': {'old': [s for s in fs if s[0] == 'old'],
                              'fixed': any(s[0] == 'fixed' for s in fs) or _fs_passthrough_24_4(text)}}


RULES = ('sdk_version', 'sub_context', 'pkg_fs_access')
LABEL = {'sdk_version': 'adapter reads SDKVersion major with split(".") (missing field = 2)',
         'sub_context': 'adapter decides sub-context by createCanvas/getSharedCanvas, not by missing getOpenDataContext',
         'pkg_fs_access': 'adapter skips fs.access for in-package (non-http, non-user-dir) files'}


def detect(files):
    """Read-only: {'target': [...], 'reason': str, 'rules': {rule: 'old'|'fixed'|'ambiguous'|'unknown'}}."""
    adapters, why = target(files)
    if not adapters:
        return {'target': [], 'reason': why, 'rules': {}}
    rules = {}
    for rule in RULES:
        old = fixed = 0
        for name in adapters:
            data = files[name]
            scan = _scan(data.decode('utf-8', 'replace') if isinstance(data, bytes) else data)[rule]
            old += len(scan['old'])
            fixed += 1 if scan['fixed'] else 0
        rules[rule] = 'ambiguous' if old > 1 else 'old' if old == 1 else 'fixed' if fixed else 'unknown'
    return {'target': adapters, 'reason': 'Cocos ' + why + ' ByteDance build', 'rules': rules}


def _rewrite(text, rule):
    scan = _scan(text)[rule]
    if len(scan['old']) != 1:
        return text, len(scan['old'])
    if rule == 'pkg_fs_access':
        _, start, _, p, cb = scan['old'][0]
        return text[:start] + FS_GUARD.format(p=p, cb=cb) + text[start:], 1
    m = scan['old'][0]
    new = (SDK_NEW if rule == 'sdk_version' else SUB_NEW).format(v=m.group(1))
    return text[:m.start()] + new + text[m.end():], 1


def apply(native_dir):
    """Rewrite old adapter forms in place. -> {'changed': [...], 'blocks': [finding...], 'target': [...], 'reason'}.
    Nothing is written unless every rule is either already fixed or matched exactly once."""
    native = Path(native_dir)
    names = {}
    for p in [native / n for n in ('game.js', 'game.json', 'project.config.json') + ADAPTER_NAMES] + \
            sorted(native.glob('cocos2d-js*.js')) + sorted(native.glob('cocos/cocos2d-js*.js')):
        rel = p.relative_to(native).as_posix()
        if p.is_file() and not p.is_symlink() and (rel in ADAPTER_NAMES or '/' not in rel or ENGINE_FILES.match(rel)):
            names[rel] = p.read_bytes()
    state = detect(names)
    out = {'changed': [], 'blocks': [], 'target': state['target'], 'reason': state['reason'], 'rules': state['rules']}
    if not state['target']:
        return out
    bad = {r: s for r, s in state['rules'].items() if s in ('ambiguous', 'unknown')}
    for rule, status in bad.items():
        out['blocks'].append(finding('ADAPTER_FIX_' + rule, 'block',
                                     'adapter version not recognised, confirm manually: %s (%s in %s; expected the stock '
                                     'Cocos 2.4 form exactly once or the fixed form)' % (LABEL[rule], status,
                                                                                         ', '.join(state['target']))))
    if bad:
        return out
    texts = {n: names[n].decode('utf-8') for n in state['target']}
    for rule in RULES:
        if state['rules'][rule] != 'old':
            continue
        for n in state['target']:
            new, count = _rewrite(texts[n], rule)
            if count == 1:
                texts[n] = new
                out['changed'].append({'file': n, 'rule': rule, 'change': LABEL[rule]})
                break
    for n, text in texts.items():
        if text.encode('utf-8') != names[n]:
            (native / n).write_bytes(text.encode('utf-8'))
    after = detect({**names, **{n: t.encode('utf-8') for n, t in texts.items()}})
    for rule, status in after['rules'].items():
        if status != 'fixed':
            out['blocks'].append(finding('ADAPTER_FIX_' + rule, 'block', 'adapter rewrite did not verify (%s): %s'
                                         % (status, LABEL[rule])))
    return out


def check(view):
    """Read-only detector for every entry: old forms are only warnings (completed games carry them)."""
    state = detect(view.files)
    out = []
    for rule, status in state['rules'].items():
        if status == 'fixed':
            continue
        level_note = {'old': 'old stock form', 'ambiguous': 'old form found more than once',
                      'unknown': 'neither the stock nor the fixed form found'}[status]
        out.append(finding('W_adapter_' + rule, 'warn', '%s: %s (%s). The writers make_tiktok_zip.py / '
                           'build_checked_zip.py rewrite it automatically; a hand-made ZIP keeps it'
                           % (LABEL[rule], level_note, ', '.join(state['target'])), {'rule': rule, 'status': status}))
    return out
