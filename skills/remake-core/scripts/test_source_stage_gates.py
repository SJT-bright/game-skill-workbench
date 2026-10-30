#!/usr/bin/env python3
"""Tests for the v7.5 source-stage gates: audit_source_appid.py, audit_platform_kit_required.py,
audit_package_estimate.py (Germ2048 items 3, 4, 6). Synthetic projects only; run: python3 -B test_source_stage_gates.py"""
import json
from pathlib import Path
import shutil
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_package_estimate as est  # noqa: E402
import audit_platform_kit_required as kitreq  # noqa: E402
import audit_source_appid as appid  # noqa: E402

KIT = HERE.parent / 'assets' / 'platform-kit'
FAILS = []


def check(name, cond, detail=''):
    print(('ok   ' if cond else 'FAIL ') + name + ('' if cond else '  ' + str(detail)[:400]))
    if not cond:
        FAILS.append(name)


def project(root, version='2.4.0'):
    root.mkdir(parents=True)
    (root / 'assets').mkdir()
    (root / 'project.json').write_text(json.dumps({'engine': 'cocos2d-html5', 'version': version}), encoding='utf-8')
    return root


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def bundle_meta(folder, subpackage):
    meta = {'ver': '1.1.2', 'uuid': '11111111-2222-3333-4444-555555555555', 'isBundle': True,
            'compressionType': {'bytedance': 'subpackage' if subpackage else 'merge_dep'}}
    folder.mkdir(parents=True, exist_ok=True)
    write(folder.with_name(folder.name + '.meta'), json.dumps(meta))


def test_appid(tmp):
    p = project(tmp / 'appid')
    r = appid.audit(p)
    check('appid: missing settings/bytedance.json -> needs_fix', r['status'] == 'needs_fix' and 'missing' in r['problems'][0], r)
    for value, want in (('testappId', 'needs_fix'), ('', 'needs_fix'), ('tt12ab', 'needs_fix'),
                        ('7683427172773644296', 'pass'), ('7712345678901234567', 'pass')):
        write(p / 'settings' / 'bytedance.json', json.dumps({'appid': value}))
        r = appid.audit(p)
        check('appid: %r -> %s' % (value, want), r['status'] == want, r)
    write(p / 'settings' / 'bytedance.json', json.dumps({'appid': '7683427172773644296'}))
    check('appid: shared test-group ID is a note, never a problem', appid.audit(p)['notes'] and not appid.audit(p)['problems'])
    p3 = project(tmp / 'appid3', '3.8.6')
    check('appid: 3.x -> not_applicable', appid.audit(p3)['status'] == 'not_applicable')


def kit_copy(p, templates=True):
    shutil.copytree(KIT / 'assets' / 'tiktok-platform', p / 'assets' / 'tiktok-platform')
    for f in (KIT / 'build-templates' / 'bytedance').iterdir() if templates else ():
        write(p / 'build-templates' / 'bytedance' / f.name, f.read_text(encoding='utf-8'))
    cfg = p / 'assets' / 'tiktok-platform' / 'PlatformConfig.js'
    # kit 2.0: normalLevelCoins (B) must be set, otherwise growthReward() throws (check_kit_project error)
    cfg.write_text(cfg.read_text(encoding='utf-8').replace("gameId: 'change-me'", "gameId: 'testgame'")
                   .replace('normalLevelCoins: 0,', 'normalLevelCoins: 12,'), encoding='utf-8')
    data = json.loads((KIT / 'settings' / 'bytedance.json').read_text(encoding='utf-8'))
    data['appid'] = '7683427172773644296'
    write(p / 'settings' / 'bytedance.json', json.dumps(data))
    bundle_meta(p / 'assets' / 'resources', True)


def test_kit_required(tmp):
    p = project(tmp / 'kit', '2.4.0')
    write(p / 'assets' / 'Script' / 'MyAds.js', 'tt.createRewardedVideoAd({adUnitId: "x"});\n')
    r = kitreq.audit(p, '2.4.15')
    check('kit: 2.4.0 project built with 2.4.15, no kit -> needs_fix', r['status'] == 'needs_fix', r)
    check('kit: missing build-templates main.js is a problem',
          any('build-templates/bytedance/main.js' in x for x in r['problems']), r['problems'])
    check('kit: missing touch-coordinates.js is a problem',
          any('touch-coordinates.js' in x for x in r['problems']), r['problems'])
    check('kit: own ad wrapper is a warning, not a problem (A1)',
          any('MyAds.js' in w for w in r['warnings']) and not any('MyAds.js' in x for x in r['problems']), r)
    check('kit: RewardedService lines are never problems (A1)', not any('RewardedService' in x for x in r['problems']), r['problems'])
    check('kit: build with 2.4.0 -> not_applicable', kitreq.audit(p, '2.4.0')['status'] == 'not_applicable')
    check('kit: 3.x project -> not_applicable', kitreq.audit(project(tmp / 'kit3', '3.8.6'), '2.4.15')['status'] == 'not_applicable')
    kit_copy(p)
    r = kitreq.audit(p, '2.4.15')
    check('kit: kit copied unchanged -> pass (wrapper still a warning)', r['status'] == 'pass' and r['warnings'], r)
    main = p / 'build-templates' / 'bytedance' / 'main.js'
    main.write_text(main.read_text(encoding='utf-8') + '\n// edited\n', encoding='utf-8')
    r = kitreq.audit(p, '2.4.15')
    check('kit: edited main.js -> needs_fix', r['status'] == 'needs_fix' and any('main.js differs' in x for x in r['problems']), r)


def test_kit_required_english(tmp):
    """v7.7 (parent decision, W-D2 REQUESTS 1 option (a)): an English project needs a fresh source-stage record
    (K5) instead of the kit build-templates; remake projects keep the build-templates rule."""
    import tiktok_finalize as F
    for how in ('docs', 'marker'):
        p = project(tmp / ('eng-' + how), '2.4.0')
        if how == 'docs':
            (p / 'docs' / 'english').mkdir(parents=True)
        else:
            write(p / '.tiktok-kit' / 'policy.json', json.dumps({'policy': 'new', 'board': 'localize'}))
        kit_copy(p, templates=False)
        r = kitreq.audit(p, '2.4.15')
        check('kit english (%s): no source record -> needs_fix' % how, r['status'] == 'needs_fix' and
              any('K5_source_finalized' in x and 'missing' in x for x in r['problems']), r['problems'])
        check('kit english (%s): build-templates not asked for' % how,
              not any('build-templates' in x for x in r['problems']), r['problems'])
        rec = F.finalize_source(p, 'localize')
        check('kit english (%s): source phase ran without blocks' % how, not rec['blocks'], rec['blocks'])
        check('kit english (%s): source phase left build-templates alone' % how,
              not (p / 'build-templates' / 'bytedance' / 'main.js').exists())
        r = kitreq.audit(p, '2.4.15')
        check('kit english (%s): fresh source record, no build-templates -> pass' % how,
              r['status'] == 'pass' and r['source_record'] == 'fresh', r)
        write(p / 'assets' / 'Script' / 'Later.js', '// edited after the source phase\n')
        r = kitreq.audit(p, '2.4.15')
        check('kit english (%s): project changed after the source phase -> needs_fix' % how,
              r['status'] == 'needs_fix' and any('changed after the source phase' in x for x in r['problems']), r)
    p = project(tmp / 'remake-with-record', '2.4.0')
    kit_copy(p, templates=False)
    F.finalize_source(p, 'remake', steps=('settings',))
    r = kitreq.audit(p, '2.4.15')
    check('kit remake: a source record does not replace the build-templates rule',
          r['status'] == 'needs_fix' and any('build-templates/bytedance/main.js' in x for x in r['problems'])
          and r['english_project'] is None, r['problems'])


def test_estimate(tmp):
    p = project(tmp / 'est', '2.4.15')
    big = p / 'assets' / 'resources' / 'big.bin'
    big.parent.mkdir(parents=True)
    big.write_bytes(b'\0' * 3_000_000)
    write(p / 'build-templates' / 'wechatgame' / 'openDataContext' / 'huge.bin', 'x' * 40)
    r = est.audit(p)
    check('estimate: main > 4 MB, resources not a subpackage -> needs_fix', r['status'] == 'needs_fix', r)
    shutil.rmtree(p / 'assets' / 'resources')
    bundle_meta(p / 'assets' / 'resources', True)
    (p / 'assets' / 'resources' / 'big.bin').write_bytes(b'\0' * 3_000_000)
    r = est.audit(p)
    check('estimate: same bytes in a ByteDance subpackage -> pass', r['status'] == 'pass', r)
    (p / 'build-templates' / 'wechatgame' / 'openDataContext' / 'huge.bin').write_bytes(b'\0' * 31_000_000)
    r = est.audit(p)
    check('estimate: wechat open-data never counts', r['status'] == 'pass', r.get('estimate'))
    (p / 'assets' / 'resources' / 'more.bin').write_bytes(b'\0' * 28_000_000)
    r = est.audit(p)
    check('estimate: total > 30 MB -> needs_fix', r['status'] == 'needs_fix', r.get('estimate'))


def main():
    tmp = Path(tempfile.mkdtemp(prefix='srcgates-'))
    try:
        test_appid(tmp)
        test_kit_required(tmp)
        test_kit_required_english(tmp)
        test_estimate(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print('%d failed' % len(FAILS) if FAILS else 'all passed')
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
