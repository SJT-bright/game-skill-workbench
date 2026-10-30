"""WebP decode gates (v7.5; Basil problem 2, LunasJade problem 2, Mabel's Meadow problem 3 - Mabel wins).

A package that ships .webp art must decide WebP support by really decoding a WebP with the TikTok image object,
because the engine's own test (canvas.toDataURL on 2.4, a lossy 1x1 data URI with img.onload on 3.x) can say
"no" on a phone that displays WebP fine; the engine then skips every texture (error 3121).

G4_webp_probe (block):
  - the package has .webp art and no root startup file runs a decode probe (tt.createImage + capabilities.webp on
    2.4, cc.sys.hasFeature on 3.x) before the engine starts;
  - the probe decodes only a data: URI (a mini-game image loader is not required to accept one; iOS reports of
    data/base64 images that never fire onload), or every .webp it names is missing or inside a subpackage (not
    downloaded yet when the probe runs);
  - capabilities.webp / hasFeature is forced to true without a decode;
  - Cocos 3.x: the art is lossless (VP8L) but the probe sample is lossy (VP8) only.
A probe that decodes a real main-package .webp first and keeps a data: URI only as a fallback is a warning.
"""
import base64
import re

from . import finding

DATA_URI = re.compile(r'data:image/webp;base64,([A-Za-z0-9+/=]+)')
WEBP_REF = re.compile(r'["\']([\w./-]+\.webp)["\']')
FORCED_CAPS = re.compile(r'(?:^|[;{}\n,(]\s*)(?:[\w$]+\.)*capabilities(?:\.webp|\[\s*["\']webp["\']\s*\])\s*=\s*(?:true|!0)\s*[;,})\n]')
FORCED_FEATURE = re.compile(r'hasFeature\s*=\s*function\s*\([^)]*\)\s*\{\s*return\s+(?:true|!0)\s*;?\s*\}')
PATCH_FEATURE = re.compile(r'\bhasFeature\s*=\s*function|overrideSettings\s*\([^)]*webp', re.I)


def webp_kind(data):
    """'lossy' (VP8), 'lossless' (VP8L) or None for one WebP file."""
    if len(data) < 16 or data[:4] != b'RIFF' or data[8:12] != b'WEBP':
        return None
    pos = 12
    while pos + 8 <= len(data):
        tag = data[pos:pos + 4]
        size = int.from_bytes(data[pos + 4:pos + 8], 'little')
        if tag == b'VP8L':
            return 'lossless'
        if tag == b'VP8 ':
            return 'lossy'
        pos += 8 + size + (size & 1)
    return None


def _probes(view):
    out = []
    for name in view.game_js():
        text = view.text(name)
        # A probe decodes a WebP sample of its own (a .webp path or a data: URI); a startup file that only
        # calls a probe module and reads capabilities.webp is not one.
        if 'createImage' in text and (DATA_URI.search(text) or WEBP_REF.search(text)) and \
                re.search(r'capabilities|hasFeature|Feature\.WEBP', text):
            out.append(name)
    return out


def _module_names(name):
    base = name.rsplit('/', 1)[-1]
    stem = base[:-3] if base.endswith('.js') else base
    return {base, stem}


def _required_by_root(view, probe):
    """True when a root startup file (other than the probe) requires the probe module."""
    names = _module_names(probe)
    for other in view.game_js():
        if '/' in other or other == probe:
            continue
        for ref in re.findall(r'require\(\s*["\']\.?/?([\w./-]+)["\']\s*\)', view.text(other)):
            if ref.rsplit('/', 1)[-1] in names:
                return True
    return False


def check(view):
    webp = [n for n in view.files if n.lower().endswith('.webp')]
    if not webp:
        return []
    out = []
    probes = _probes(view)
    sample_names = set()
    for name in probes:
        for ref in WEBP_REF.findall(view.text(name)):
            sample_names.add(ref.lstrip('./'))
    art = [n for n in webp if n not in sample_names]
    if not art:
        return []
    engine = view.engine_major
    # Forced "supported" anywhere in game code.
    for name in view.game_js():
        text = view.text(name)
        if FORCED_CAPS.search(text) or FORCED_FEATURE.search(text):
            out.append(finding('G4_webp_probe', 'block',
                               '%s turns WebP support on without decoding anything' % name, {'file': name}))
    boot = [p for p in probes if '/' not in p and (p in ('game.js', 'main.js') or _required_by_root(view, p))]
    if engine == 3:
        boot = [p for p in boot if PATCH_FEATURE.search(view.text(p)) or 'hasFeature' in view.text(p)]
    if not boot:
        # v7.5: block on 2.4 (Mabel r7); warning on 3.x, where the engine's format selection may never pick WebP
        # (Marlows R5/R6 were falsely refused, cross-game summary IM3); v7.6 checks the ImageAsset formats first.
        out.append(finding('G4_webp_probe', 'warn' if engine == 3 else 'block',
                           'the package ships %d .webp file(s) but no root startup file decodes a WebP with '
                           'tt.createImage before the engine starts (%s)'
                           % (len(art), 'report through cc.sys.hasFeature' if engine == 3 else
                              'set cc.sys.capabilities.webp only after a real decode'),
                           {'webp_files': len(art), 'probe_candidates': probes}))
        return out
    samples = []          # (source, bytes)
    for probe in boot:
        text = view.text(probe)
        uris = DATA_URI.findall(text)
        refs = [r.lstrip('./') for r in WEBP_REF.findall(text)]
        good, bad = [], []
        for ref in refs:
            if ref not in view.files:
                bad.append('%s (not in the package)' % ref)
            elif view.subpackage_of(ref):
                bad.append('%s (inside subpackage %s)' % (ref, view.subpackage_of(ref)['root']))
            else:
                good.append(ref)
                samples.append((ref, view.files[ref]))
        for uri in uris:
            try:
                samples.append(('data: URI', base64.b64decode(uri + '=' * (-len(uri) % 4))))
            except (ValueError, TypeError):
                pass
        if not good:
            if uris:
                reason = 'decodes a data: URI; probe a real .webp file shipped in the main package'
            elif bad:
                reason = 'names %s; the probed .webp must be in the main package' % ', '.join(bad)
            else:
                reason = 'names no .webp file to decode'
            out.append(finding('G4_webp_probe', 'block', '%s %s' % (probe, reason),
                               {'probe': probe, 'data_uri': bool(uris), 'refs': refs}))
        elif uris:
            out.append(finding('G4_webp_probe', 'warn',
                               '%s decodes %s first but keeps a data: URI fallback; drop the data: URI'
                               % (probe, ', '.join(good)), {'probe': probe}))
    # Lossless art probed with a lossy sample only.
    art_kinds = {webp_kind(view.files[n]) for n in art}
    sample_kinds = {webp_kind(data) for _, data in samples} - {None}
    if 'lossless' in art_kinds and sample_kinds and 'lossless' not in sample_kinds:
        out.append(finding('G4_webp_probe', 'block' if engine == 3 else 'warn',
                           'the art is lossless WebP (VP8L) but the probe sample is lossy (VP8) only; probe a sample '
                           'encoded like the art', {'art': sorted(k for k in art_kinds if k), 'samples': sorted(sample_kinds)}))
    return out
