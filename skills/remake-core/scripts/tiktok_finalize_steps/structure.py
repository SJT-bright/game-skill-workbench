"""Native step: package structure and debug code (design D77 1.3 row structure.py, 3.6, 3.8 L4, Q7). Check only.

block in both policies: 0-byte files, a path with a '..' segment or a symlink (a ZIP must not point outside).
new policy blocks / legacy warns:
    K_S_webp       a .webp file in the build (new games ship PNG/JPG; the --keep-webp-exception case is allowed
                   only together with the kit WebP probe part webp_probe24 installed)
    L4_debug_code  debug switches, a mock ad window or a test level skip in game JavaScript (engine and adapter
                   excluded). Patterns are kept narrow; calibration on completed games is listed in RESULT.md.
warning only (Q7): identical files of 1 KB or more (bytes that could be saved, the file names; never deleted).
"""
import re
from collections import defaultdict

from . import Result, is_engine_or_adapter, sha256, text_of

STEP = 'structure'
DEBUG = [
    ('stats_on', re.compile(r'\bcc\.debug\.setDisplayStats\(\s*(?:true|!0)\s*\)')),
    ('vconsole', re.compile(r'\bnew\s+VConsole\s*\(|window\.VConsole\b')),
    ('qa_switch', re.compile(r'\b__qa[A-Z_]\w*\s*=\s*(?:true|!0)|\bwindow\.__qa\b')),
    ('debug_flag', re.compile(r'\b(?:DEBUG|DEBUG_MODE|IS_DEBUG|debugMode)\s*[:=]\s*(?:true|!0)\b')),
    ('diagnostic_ui', re.compile(r'\bcc\.Node\(\s*["\'][\w-]*(?:Diagnostic|DebugPanel|DebugBadge|DebugLabel)'
                                 r'[\w-]*["\']\s*\)')),
    ('mock_ad', re.compile(r'\b(?:mock|fake)(?:Rewarded|Reward|Video)?Ad\w*\s*[:=(]|模拟广告|假广告')),
    ('test_skip', re.compile(r'\b(?:debugSkipLevel|skipLevelForTest|cheatSkip|testSkipLevel|unlockAllLevels)\b'
                             r'\s*[:=(]')),
]
DEBUG_FILES = re.compile(r'(^|/)vconsole(\.min)?\.js$', re.I)
DUP_MIN = 1024


def findings(files, policy, options=None, manifest=None, symlinks=()):
    options = options or {}
    level = 'block' if policy == 'new' else 'warn'
    out = []
    zero = sorted(n for n, d in files.items() if not d)
    if zero:
        out.append({'id': 'K_S_zero_byte', 'level': 'block', 'message': '%d empty file(s): %s'
                    % (len(zero), ', '.join(zero[:5])), 'evidence': zero[:20]})
    bad = sorted(n for n in files if '..' in n.split('/') or n.startswith('/')) + sorted(symlinks)
    if bad:
        out.append({'id': 'K_S_outside_path', 'level': 'block', 'message': "path outside the package ('..' or "
                    'symlink): %s' % ', '.join(bad[:5]), 'evidence': bad[:20]})
    webp = sorted(n for n in files if n.lower().endswith('.webp'))
    if webp:
        probe = manifest and any((p.get('file') or {}).get('dest') in files and
                                 sha256(files[(p.get('file') or {})['dest']]) == (p.get('file') or {}).get('sha256')
                                 for n, p in manifest.parts.items() if n.startswith('webp_probe'))
        allowed = options.get('keep_webp_exception') and probe
        if not allowed:
            out.append({'id': 'K_S_webp', 'level': level, 'message': '%d .webp file(s) in the build (%s)%s'
                        % (len(webp), ', '.join(webp[:3]), '' if policy == 'new' else '; legacy game: the kit WebP '
                           'probe gate (webp.py G4) applies'), 'evidence': webp[:20]})
    hits = defaultdict(list)
    for name, data in sorted(files.items()):
        if DEBUG_FILES.search(name):
            hits['vconsole'].append(name)
        if not name.endswith('.js') or is_engine_or_adapter(name):
            continue
        text = text_of(data)
        for key, rx in DEBUG:
            m = rx.search(text)
            if m:
                hits[key].append('%s: %s' % (name, text[max(0, m.start() - 30):m.end() + 30].replace('\n', ' ')))
    for key, where in sorted(hits.items()):
        out.append({'id': 'L4_debug_code', 'level': level, 'message': 'debug code (%s) in %s' % (key, where[0][:160]),
                    'evidence': {'kind': key, 'where': where[:5]}})
    groups = defaultdict(list)
    for name, data in files.items():
        if len(data) >= DUP_MIN and not name.endswith(('.js', '.json')):
            groups[sha256(data)].append(name)
    dups = sorted((len(files[v[0]]) * (len(v) - 1), sorted(v)) for v in groups.values() if len(v) > 1)
    if dups:
        saved = sum(s for s, _ in dups)
        out.append({'id': 'W_duplicate_files', 'level': 'warn', 'message': '%d group(s) of identical files, %d bytes '
                    'could be saved (report only, Q7; remove in the art step)' % (len(dups), saved),
                    'evidence': [{'bytes': s, 'files': v[:4]} for s, v in reversed(dups[-10:])]})
    return out


def verify(files, manifest=None, policy='new', options=None):
    return findings(files, policy, options, manifest)


def detect(ctx):
    return 'conflict' if any(f['level'] == 'block' for f in verify(ctx.files(), ctx.manifest, ctx.policy,
                                                                    ctx.options)) else 'kit_current'


def apply(ctx):
    r = Result(STEP)
    links = sorted(p.relative_to(ctx.root).as_posix() for p in ctx.root.rglob('*') if p.is_symlink())
    for item in findings(ctx.files(), ctx.policy, ctx.options, ctx.manifest, links):
        (r.blocks if item['level'] == 'block' else r.warnings).append(item)
    r.state = 'conflict' if r.blocks else 'kit_current'
    return r.as_dict()
