#!/usr/bin/env python3
"""tiktok_finalize image steps (v7.7 W-C): images.py (source), png.py (native), finalize_images_compare.py.

Synthetic 2.4 and 3.x projects only; real-package results are in the W-C RESULT, not here.
Run: python3 test_finalize_images.py   (prints JSON, exit 1 on the first failed case)
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from PIL import Image  # noqa: E402

from tiktok_finalize_steps import Ctx, Manifest, images, png  # noqa: E402
import finalize_images_compare as compare  # noqa: E402

results = []


def check(name, cond, detail=None):
    if not cond:
        print(json.dumps({'status': 'fail', 'case': name, 'detail': detail}, indent=1, default=str))
        sys.exit(1)
    results.append(name)


def gradient(w, h, alpha=False, seed=0):
    im = Image.new('RGBA' if alpha else 'RGB', (w, h))
    px = im.load()
    for y in range(h):
        for x in range(w):
            c = ((x * 7 + seed) % 256, (y * 5) % 256, ((x + y) * 3) % 256)
            px[x, y] = c + ((0 if x < w // 4 else 255),) if alpha else c
    return im


def noisy(w, h, seed=0):
    import random
    rnd = random.Random(seed)
    im = Image.new('RGBA', (w, h))
    px = im.load()
    for y in range(h):
        for x in range(w):
            px[x, y] = (rnd.randrange(256), (y * 3) % 256, rnd.randrange(256), 255 if x > 8 else 0)
    return im


def uid(n):
    return '%08x-1111-4222-8333-%012x' % (n, n)


def meta24(name, n, w, h, trim=False):
    stem = name.rsplit('.', 1)[0]
    return {'ver': '2.3.5', 'uuid': uid(n), 'type': 'sprite', 'width': w, 'height': h, 'platformSettings': {},
            'subMetas': {stem: {'ver': '1.0.4', 'uuid': uid(n + 1000), 'rawTextureUuid': uid(n),
                                'trimX': 3 if trim else 0, 'trimY': 0, 'offsetX': 0, 'offsetY': 0,
                                'width': w - (6 if trim else 0), 'height': h, 'rawWidth': w, 'rawHeight': h,
                                'borderTop': 0, 'borderBottom': 0, 'borderLeft': 0, 'borderRight': 0,
                                'subMetas': {}}}}


def meta3(name, n, w, h, alpha):
    ext = '.' + name.rsplit('.', 1)[1]
    return {'ver': '1.0.27', 'importer': 'image', 'imported': True, 'uuid': uid(n), 'files': ['.json', ext],
            'subMetas': {'6c48a': {'importer': 'texture', 'uuid': uid(n) + '@6c48a', 'userData': {}},
                         'f9941': {'importer': 'sprite-frame', 'uuid': uid(n) + '@f9941',
                                   'userData': {'trimX': 0, 'trimY': 0, 'offsetX': 0, 'offsetY': 0, 'width': w,
                                                'height': h, 'rawWidth': w, 'rawHeight': h,
                                                'vertices': {'rawPosition': [-w / 2, -h / 2, 0, w / 2, h / 2, 0],
                                                             'uv': [0, h, w, 0], 'minPos': [-w / 2, -h / 2, 0],
                                                             'maxPos': [w / 2, h / 2, 0]}}}},
            'userData': {'type': 'sprite-frame', 'hasAlpha': alpha}}


def scene24(sprites):
    """sprites: [(frame uuid, display w, display h)] -> 2.4 .fire object list."""
    objs = [{'__type__': 'cc.SceneAsset'}, {'__type__': 'cc.Scene'}]
    for frame, w, h in sprites:
        node = len(objs)
        objs.append({'__type__': 'cc.Node', '_contentSize': {'width': w, 'height': h},
                     '_trs': {'array': [0, 0, 0, 0, 0, 0, 1, 1, 1, 1]}, '_components': [{'__id__': node + 1}]})
        objs.append({'__type__': 'cc.Sprite', 'node': {'__id__': node}, '_spriteFrame': {'__uuid__': frame},
                     '_type': 0, '_sizeMode': 1})
    return objs


def scene3(sprites):
    objs = [{'__type__': 'cc.SceneAsset'}, {'__type__': 'cc.Scene'}]
    for frame, w, h in sprites:
        node = len(objs)
        objs.append({'__type__': 'cc.Node', '_lscale': {'x': 1, 'y': 1},
                     '_components': [{'__id__': node + 1}, {'__id__': node + 2}]})
        objs.append({'__type__': 'cc.UITransform', 'node': {'__id__': node}, '_contentSize': {'width': w, 'height': h}})
        objs.append({'__type__': 'cc.Sprite', 'node': {'__id__': node}, '_spriteFrame': {'__uuid__': frame},
                     '_type': 0, '_sizeMode': 1})
    return objs


def put(project, rel, im, meta, fmt='WEBP'):
    p = project / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    kw = {'lossless': True, 'exact': True} if fmt == 'WEBP' else {}
    im.save(p, fmt, **kw)
    p.with_name(p.name + '.meta').write_text(json.dumps(meta, indent=2))
    return p


def project24(root):
    proj = root / 'p24'
    (proj / 'assets').mkdir(parents=True)
    (proj / 'project.json').write_text(json.dumps({'engine': 'cocos2d-html5', 'version': '2.4.15'}))
    put(proj, 'assets/ui/hero.webp', gradient(64, 64, alpha=True), meta24('hero.webp', 1, 64, 64))
    put(proj, 'assets/ui/bg.webp', gradient(64, 96), meta24('bg.webp', 2, 64, 96))
    put(proj, 'assets/ui/big.png', gradient(400, 200), meta24('big.png', 3, 400, 200), 'PNG')      # 4x display
    put(proj, 'assets/ui/near.png', gradient(150, 75), meta24('near.png', 4, 150, 75), 'PNG')      # 1.5x display
    put(proj, 'assets/ui/trim.png', gradient(400, 200), meta24('trim.png', 5, 400, 200, trim=True), 'PNG')
    m = meta24('packed.webp', 6, 32, 32)
    m['platformSettings'] = {'bytedance': {'formats': [{'name': 'webp', 'quality': 80}]}}
    put(proj, 'assets/ui/packed.webp', gradient(32, 32, alpha=True), m)
    fire = scene24([(uid(1001), 64, 64), (uid(1002), 64, 96), (uid(1003), 100, 50), (uid(1004), 100, 50),
                    (uid(1005), 100, 50), (uid(1006), 32, 32)])
    (proj / 'assets' / 'main.fire').write_text(json.dumps(fire))
    return proj


def project3(root):
    proj = root / 'p3'
    (proj / 'assets').mkdir(parents=True)
    (proj / 'package.json').write_text(json.dumps({'creator': {'version': '3.8.8'}}))
    put(proj, 'assets/art/hero.webp', gradient(64, 64, alpha=True), meta3('hero.webp', 11, 64, 64, True))
    put(proj, 'assets/art/bg.webp', gradient(64, 96), meta3('bg.webp', 12, 64, 96, False))
    put(proj, 'assets/art/big.png', gradient(400, 200), meta3('big.png', 13, 400, 200, False), 'PNG')
    m = meta3('comp.png', 14, 32, 32, False)
    m['userData']['compressSettings'] = {'useCompressTexture': True, 'presetId': 'mmc-webp'}
    put(proj, 'assets/art/comp.png', gradient(32, 32), m, 'PNG')
    cfg = proj / 'settings' / 'v2' / 'packages' / 'builder.json'
    cfg.parent.mkdir(parents=True)
    cfg.write_text(json.dumps({'textureCompressConfig': {'userPreset': {'mmc-webp': {
        'options': {'miniGame': {'webp': {'quality': 80}}}}}}}))
    scene = scene3([(uid(11) + '@f9941', 64, 64), (uid(12) + '@f9941', 64, 96), (uid(13) + '@f9941', 100, 50),
                    (uid(14) + '@f9941', 32, 32)])
    (proj / 'assets' / 'main.scene').write_text(json.dumps(scene))
    return proj


def tree_bytes(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob('*')) if p.is_file()}


def meta_of(path):
    return json.loads(Path(str(path) + '.meta').read_text())


with tempfile.TemporaryDirectory(prefix='finalize-images ') as td:
    root = Path(td)

    # ---------------- 2.4: convert, keep uuid, compression webp off, resize only above 2x
    p24 = project24(root)
    r = images.apply({'project': p24, 'policy': 'new'})
    check('24-apply-no-blocks', not r['blocks'], r['blocks'])
    a = p24 / 'assets' / 'ui'
    check('24-alpha-webp-to-png', (a / 'hero.png').is_file() and not (a / 'hero.webp').exists()
          and Image.open(a / 'hero.png').format == 'PNG')
    check('24-opaque-webp-to-jpg', (a / 'bg.jpg').is_file() and Image.open(a / 'bg.jpg').format == 'JPEG')
    check('24-meta-renamed-uuid-kept', meta_of(a / 'hero.png')['uuid'] == uid(1) and meta_of(a / 'bg.jpg')['uuid'] == uid(2)
          and not (a / 'hero.webp.meta').exists() and not (a / 'bg.webp.meta').exists())
    check('24-frame-uuid-kept', meta_of(a / 'hero.png')['subMetas']['hero']['uuid'] == uid(1001))
    check('24-png-lossless', Image.open(a / 'hero.png').convert('RGBA').tobytes()
          == gradient(64, 64, alpha=True).tobytes())
    check('24-no-webp-left', not list((p24 / 'assets').rglob('*.webp')))
    check('24-compress-webp-off', 'bytedance' not in meta_of(a / 'packed.png')['platformSettings'])
    big = meta_of(a / 'big.png')
    check('24-shrunk-above-2x', Image.open(a / 'big.png').size == (200, 100) and big['width'] == 200
          and big['subMetas']['big']['rawWidth'] == 200 and big['subMetas']['big']['height'] == 100, big)
    check('24-not-shrunk-within-2x', Image.open(a / 'near.png').size == (150, 75))
    check('24-trimmed-not-shrunk', Image.open(a / 'trim.png').size == (400, 200))
    fire = json.loads((p24 / 'assets' / 'main.fire').read_text())
    check('24-shrunk-sprite-custom-size', fire[7]['_sizeMode'] == 0 and fire[9]['_sizeMode'] == 1, fire[7])
    orig = p24 / '.tiktok-kit' / 'originals' / 'assets' / 'ui'
    check('24-originals-backed-up', (orig / 'hero.webp').is_file() and (orig / 'big.png').is_file()
          and Image.open(orig / 'big.png').size == (400, 200))
    before = tree_bytes(p24 / 'assets')
    r2 = images.apply({'project': p24, 'policy': 'new'})
    check('24-second-run-no-change', not r2['changed'] and not r2['blocks'] and tree_bytes(p24 / 'assets') == before
          and r2['state'] == 'kit_current', r2['changed'][:3])
    check('24-detect-current', images.detect({'project': p24, 'policy': 'new'}) == 'kit_current')

    # ---------------- 3.x
    p3 = project3(root)
    r = images.apply({'project': p3, 'policy': 'new'})
    b = p3 / 'assets' / 'art'
    check('3x-apply-no-blocks', not r['blocks'], r['blocks'])
    m = meta_of(b / 'hero.png')
    check('3x-alpha-to-png-meta', m['uuid'] == uid(11) and m['files'] == ['.json', '.png'] and m['userData']['hasAlpha'] is True
          and m['importer'] == 'image', m)
    m = meta_of(b / 'bg.jpg')
    check('3x-opaque-to-jpg-meta', Image.open(b / 'bg.jpg').format == 'JPEG' and m['files'] == ['.json', '.jpg']
          and m['subMetas']['f9941']['uuid'] == uid(12) + '@f9941' and m['userData']['hasAlpha'] is False, m)
    m = meta_of(b / 'big.png')
    ud = m['subMetas']['f9941']['userData']
    check('3x-shrunk-geometry', Image.open(b / 'big.png').size == (200, 100) and ud['width'] == 200
          and ud['vertices']['rawPosition'][3] == 100 and ud['vertices']['uv'][2] == 200, ud)
    check('3x-compress-preset-webp-off', meta_of(b / 'comp.png')['userData']['compressSettings']['useCompressTexture'] is False)
    check('3x-second-run-no-change', not images.apply({'project': p3, 'policy': 'new'})['changed'])

    # ---------------- refusals and legacy
    pl = project24(root / 'legacy')
    snap = tree_bytes(pl)
    r = images.apply({'project': pl, 'policy': 'legacy'})
    check('legacy-changes-nothing', not r['changed'] and tree_bytes(pl) == snap and r['warnings'], r)
    ps = project24(root / 'script')
    (ps / 'assets' / 'Game.js').write_text("cc.resources.load('ui/hero.webp')")
    r = images.apply({'project': ps, 'policy': 'new'})
    check('script-names-webp-refused', r['blocks'] and (ps / 'assets' / 'ui' / 'hero.webp').is_file()
          and not (ps / '.tiktok-kit' / 'originals').exists(), r['blocks'])
    pn = project24(root / 'nometa')
    (pn / 'assets' / 'ui' / 'bg.webp.meta').unlink()
    check('webp-without-meta-refused', images.apply({'project': pn, 'policy': 'new'})['blocks'])

    # ---------------- image-overrides.json
    po = project24(root / 'ovr')
    (po / '.tiktok-kit').mkdir()
    (po / '.tiktok-kit' / 'image-overrides.json').write_text(json.dumps({'images': {
        'assets/ui/bg.webp': {'format': 'png'}, 'assets/ui/big.png': {'resize': False}}}))
    images.apply({'project': po, 'policy': 'new'})
    check('override-format', (po / 'assets/ui/bg.png').is_file() and not (po / 'assets/ui/bg.jpg').exists())
    check('override-resize-false', Image.open(po / 'assets/ui/big.png').size == (400, 200))
    (po / '.tiktok-kit' / 'image-overrides.json').write_text(json.dumps({'images': {'x.webp': {'format': 'gif'}}}))
    check('override-invalid-refused', images.apply({'project': po, 'policy': 'new'})['blocks'])
    (po / '.tiktok-kit' / 'image-overrides.json').write_text(json.dumps({'images': {
        'assets/ui/hero.webp': {'format': 'jpg'}}}))
    pa = project24(root / 'alphajpg')
    shutil.copytree(po / '.tiktok-kit', pa / '.tiktok-kit')
    check('override-jpg-on-alpha-refused', images.apply({'project': pa, 'policy': 'new'})['blocks'])

    # max_side (explicit shrink of trimmed / code-loaded art) with a glob key
    pm = project24(root / 'maxside')
    (pm / 'assets' / 'resources').mkdir()
    shutil.move(str(pm / 'assets/ui/trim.png'), str(pm / 'assets/resources/trim.png'))
    shutil.move(str(pm / 'assets/ui/trim.png.meta'), str(pm / 'assets/resources/trim.png.meta'))
    (pm / '.tiktok-kit').mkdir()
    (pm / '.tiktok-kit' / 'image-overrides.json').write_text(json.dumps({'images': {
        'assets/resources/*.png': {'max_side': 200}}}))
    r = images.apply({'project': pm, 'policy': 'new'})
    tm = meta_of(pm / 'assets/resources/trim.png')['subMetas']['trim']
    check('max-side-glob-shrinks-trimmed-loadable', not r['blocks'] and
          Image.open(pm / 'assets/resources/trim.png').size == (200, 100) and tm['rawWidth'] == 200
          and tm['trimX'] == 2 and tm['width'] == 197, tm)
    (pm / '.tiktok-kit' / 'image-overrides.json').write_text(json.dumps({'images': {'x.png': {'max_side': 10}}}))
    check('max-side-out-of-range-refused', images.apply({'project': pm, 'policy': 'new'})['blocks'])

    # Q4 exception: new game keeps WebP only with a reason, and says so
    pe = project24(root / 'exc')
    r = images.apply({'project': pe, 'policy': 'new', 'options': {'keep_webp_exception': 'still 45 MB'}})
    check('exception-keeps-webp-with-warning', not r['blocks'] and (pe / 'assets/ui/hero.webp').is_file()
          and any('keep-webp-exception' in w['message'] for w in r['warnings'])
          and Image.open(pe / 'assets/ui/big.png').size == (200, 100), r['blocks'])

    # ---------------- png.py on a build folder
    nat = root / 'native'
    d = nat / 'assets' / 'main' / 'native' / 'ab'
    d.mkdir(parents=True)
    noisy(256, 256, seed=1).save(d / (uid(1) + '.png'))
    noisy(256, 256, seed=2).save(d / (uid(3) + '.1a2b3.png'))
    proj = root / 'pngproj'
    (proj / 'assets').mkdir(parents=True)
    ctx = Ctx('native', nat, project=proj, policy='new')
    check('png-detect-absent', png.detect(ctx) == 'absent')
    r = png.apply(ctx)
    check('png-compressed', not r['blocks'] and len(r['changed']) == 2
          and all(Image.open(p).mode == 'P' for p in d.iterdir()), r)
    cache = json.loads((proj / '.tiktok-kit' / 'png-cache.json').read_text())
    check('png-cache-written', cache['pngquant'] and cache['args'] == png.ARGS and len(cache['entries']) >= 2)
    snap = tree_bytes(nat)
    r = png.apply(ctx)
    check('png-second-run-no-change', not r['changed'] and tree_bytes(nat) == snap and r['state'] == 'kit_current', r)
    check('png-detect-current', png.detect(ctx) == 'kit_current')
    (proj / '.tiktok-kit' / 'png-cache.json').write_text(json.dumps(dict(cache, pngquant='0.0.0')))
    r = png.apply(ctx)
    check('png-cache-other-version-dropped', any('discarded' in w['message'] for w in r['warnings']), r['warnings'])

    # determinism: two fresh copies give the same bytes
    nat2 = root / 'native2'
    d2 = nat2 / 'assets' / 'x'
    d2.mkdir(parents=True)
    noisy(200, 120, seed=5).save(d2 / 'a.png')
    nat3 = root / 'native3'
    shutil.copytree(nat2, nat3)
    png.apply(Ctx('native', nat2, project=root / 'c2', policy='new'))
    png.apply(Ctx('native', nat3, project=root / 'c3', policy='new'))
    check('png-deterministic', tree_bytes(nat2) == tree_bytes(nat3) and tree_bytes(nat2) != {})

    # quantize=false via image-overrides, found in the build by uuid
    nq = root / 'nq'
    nqp = nq / 'proj'
    put(nqp, 'assets/ui/sky.png', gradient(128, 128, alpha=True), meta24('sky.png', 21, 128, 128), 'PNG')
    (nqp / '.tiktok-kit').mkdir()
    (nqp / '.tiktok-kit' / 'image-overrides.json').write_text(json.dumps({'images': {
        'assets/ui/sky.webp': {'quantize': False}, 'assets/ui/none.png': {'quantize': False}}}))
    nn = nq / 'native' / 'res' / 'raw-assets' / 'aa'
    nn.mkdir(parents=True)
    shutil.copy(nqp / 'assets/ui/sky.png', nn / (uid(21) + '.9f8e7.png'))
    noisy(128, 128, seed=9).save(nn / 'other.png')
    r = png.apply(Ctx('native', nq / 'native', project=nqp, policy='legacy'))
    check('override-missing-image-refused', r['blocks'], r)
    (nqp / '.tiktok-kit' / 'image-overrides.json').write_text(json.dumps({'images': {
        'assets/ui/sky.webp': {'quantize': False}}}))
    keep = (nn / (uid(21) + '.9f8e7.png')).read_bytes()
    r = png.apply(Ctx('native', nq / 'native', project=nqp, policy='legacy'))
    check('override-quantize-false-kept', not r['blocks'] and (nn / (uid(21) + '.9f8e7.png')).read_bytes() == keep
          and Image.open(nn / 'other.png').mode == 'P', r)

    # no --project (W-B pkg85 case): self-check must pass, cache lives beside the build, second run unchanged
    npn = root / 'noproj' / 'native'
    (npn / 'assets' / 'internal' / 'native' / '02').mkdir(parents=True)
    noisy(96, 96, seed=11).save(npn / 'assets/internal/native/02' / (uid(31) + '.png'))
    noisy(96, 96, seed=12).save(npn / 'assets/internal/native/02' / (uid(32) + '.png'))
    r = png.apply(Ctx('native', npn, policy='legacy'))
    side = root / 'noproj' / '.tiktok-kit-png-cache' / 'native.json'
    check('no-project-self-check-passes', not r['blocks'] and len(r['changed']) == 2 and side.is_file()
          and not list(npn.rglob('*.json')), r['blocks'])
    snap = tree_bytes(npn)
    r = png.apply(Ctx('native', npn, policy='legacy'))
    check('no-project-second-run-no-change', not r['changed'] and not r['blocks'] and tree_bytes(npn) == snap, r)

    # pngquant missing
    r = png.apply(Ctx('native', nat2, project=root / 'c2', options={'pngquant': str(root / 'no-pngquant')}))
    check('png-missing-pngquant-refused', r['blocks'] and r['state'] == 'conflict', r)

    # ---------------- verify (kit_parts gate view)
    man = Manifest({'version': '2.0', 'parts': {'webp_probe24': {'engine': 2, 'file': {
        'src': 'x', 'sha256': png.sha256(b'probe-js'), 'previous_sha256': []}}}}, root)
    files = {'game.js': b'x', 'assets/main/native/a.webp': b'RIFF'}
    check('verify-new-webp-blocked', [f['level'] for f in images.verify(files, man, 'new')] == ['block'])
    check('verify-new-webp-with-kit-probe-warn',
          [f['level'] for f in images.verify(dict(files, **{'webp-decode-probe.js': b'probe-js'}), man, 'new')] == ['warn'])
    check('verify-own-probe-still-blocked',
          [f['level'] for f in images.verify(dict(files, **{'webp-decode-probe.js': b'my-probe'}), man, 'new')] == ['block'])
    check('verify-legacy-warn', [f['level'] for f in images.verify(files, man, 'legacy')] == ['warn'])
    check('verify-clean-package', images.verify({'game.js': b'x', 'a.png': b'p'}, man, 'new') == [])
    check('verify-own-root-probe-image-blocked',
          [f['level'] for f in images.verify({'game.js': b'x', 'webp-probe.webp': b'R'}, man, 'new')] == ['block'])
    check('verify-kit-probe-image-alone-ok', images.verify({'loading/webp-probe.webp': b'R'}, man, 'new') == [])

    # ---------------- comparison sheet
    g = Image.new('RGB', (256, 256))
    px = g.load()
    for y in range(256):
        for x in range(256):
            px[x, y] = (x // 2 + 40, y // 2 + 60, (x + y) // 4 + 80)
    from PIL import ImageOps
    check('compare-banding-flagged', compare.metrics(g, ImageOps.posterize(g, 3))['verdict'] == 'check')
    check('compare-identical-ok', compare.metrics(g, g.copy())['verdict'] == 'ok')
    rep = compare.compare(p24)
    out = p24 / '.tiktok-kit' / 'image-compare'
    check('compare-writes-report', rep['images'] >= 6 and (out / 'index.html').is_file()
          and (out / 'suggested-overrides.json').is_file() and any(r['before'].endswith('.webp') for r in rep['rows']), rep)

print(json.dumps({'status': 'pass', 'cases': len(results), 'names': results}, indent=1))
