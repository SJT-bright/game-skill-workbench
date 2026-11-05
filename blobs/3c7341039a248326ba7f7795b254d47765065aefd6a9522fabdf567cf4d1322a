"""简化.11.14 R4A (生成时预防 P01-2): the package checks recognise the platform kit's own rewarded-guard.js.

The kit main.js v1.7 installs parts/rewarded-guard.js in every 2.4 package. The file names createRewardedVideoAd
(it wraps it). Before R4A every check that looked for that name (ad_regression.needs_regression, runtime_regression
'rewarded_ads', package gate A1/A2) would have counted the guard as a game ad caller, so every package would have
needed the rewarded-ad regression and an adapter. Now the unchanged guard is recognised by its KIT_MANIFEST sha256:
  - a package whose only rewarded-ad text is the kit guard needs no ad regression;
  - a game module that calls createRewardedVideoAd itself is still a caller (and A1 still blocks a new game);
  - a changed guard (other bytes) counts as game code;
  - an unreadable KIT_MANIFEST recognises nothing (stricter, never looser).
Seconds, no browser. On the 11.14 tree before R4A the first and fourth tests fail (the guard counts as a caller).
"""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
SHARED = HERE.parents[2] / 'remake-core' / 'scripts'
KIT = SHARED.parent / 'assets' / 'platform-kit'
for p in (HERE, SHARED):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import ad_regression  # noqa: E402
import runtime_regression  # noqa: E402
import package_gates  # noqa: E402
from package_gates import ads_static  # noqa: E402

GUARD = (KIT / 'parts' / 'rewarded-guard.js').read_bytes()
MAIN = (KIT / 'build-templates' / 'bytedance' / 'main.js').read_bytes()
GAME = b"require('./main');\n"
PLAIN = b'cc._RF.push(module, "a1b2c", "HomePage"); cc.Class({ extends: cc.Component, onLoad: function () {} });\n'
# 埃及宝石-style own ad manager (game code calling the SDK itself)
OWN_AD = (b'cc._RF.push(module, "d4e5f", "AdManager"); var AdManager = { show: function (cb) {'
          b' var ad = tt.createRewardedVideoAd({adUnitId: "x"}); ad.onClose(function (r) { cb(r && r.isEnded); });'
          b' ad.show(); } };\n')


def package(extra=None, guard=GUARD):
    files = {'game.js': GAME, 'main.js': MAIN, 'src/project.js': PLAIN}
    if guard is not None:
        files['rewarded-guard.js'] = guard
    files.update(extra or {})
    return files


def a1(files, policy='new'):
    out = package_gates.run(files, board='remake', modules=('ads_static',), policy=policy)
    return [f for f in out['blocks'] + out['warnings'] if f['id'].startswith('A1')]


class KitGuardRecognised(unittest.TestCase):
    def test_guard_only_package_needs_no_ad_regression(self):
        files = package()
        self.assertIn(b'createRewardedVideoAd', files['rewarded-guard.js'])   # why the old scan counted it
        # behaviour first, so the 11.14 tree before R4A fails here (not on a missing name)
        self.assertFalse(ad_regression.needs_regression(files), 'kit guard alone must not require the ad regression')
        self.assertFalse(runtime_regression.predicate('rewarded_ads', files, {}), 'nor the rewarded_ads suite')
        self.assertEqual(a1(files), [])
        self.assertEqual(ads_static.rewarded_callers(files), [])

    def test_game_own_ad_call_still_requires_regression_and_blocks(self):
        files = package({'src/ads.js': OWN_AD})
        self.assertEqual(ads_static.rewarded_callers(files), ['src/ads.js'])
        self.assertTrue(ad_regression.needs_regression(files))
        self.assertTrue(runtime_regression.predicate('rewarded_ads', files, {}))
        found = a1(files)
        self.assertEqual([f['level'] for f in found], ['block'])
        self.assertIn('AdManager', found[0]['message'])
        self.assertNotIn('rewarded-guard', found[0]['message'])

    def test_changed_guard_counts_as_game_code(self):
        files = package(guard=GUARD + b'\n// edited by hand\n')
        self.assertEqual(ads_static.rewarded_callers(files), ['rewarded-guard.js'])
        self.assertTrue(ad_regression.needs_regression(files))

    def test_hash_comes_from_kit_manifest(self):
        hashes = ads_static.kit_guard_hashes()
        self.assertIn(hashlib.sha256(GUARD).hexdigest(), hashes)
        manifest = json.loads((KIT / 'KIT_MANIFEST.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['parts']['rewarded24']['file']['sha256'], hashlib.sha256(GUARD).hexdigest())
        extras = {x['dest']: x['sha256'] for x in manifest['parts']['startup24']['extra_files']}
        self.assertEqual(extras.get('rewarded-guard.js'), hashlib.sha256(GUARD).hexdigest())

    def test_unreadable_manifest_recognises_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / 'KIT_MANIFEST.json'
            bad.write_text('{not json', encoding='utf-8')
            with mock.patch.object(ads_static, 'KIT_MANIFEST', bad):
                self.assertEqual(ads_static.kit_guard_hashes(), frozenset())
                self.assertEqual(ads_static.rewarded_callers(package()), ['rewarded-guard.js'])
                self.assertTrue(ad_regression.needs_regression(package()))

    def test_package_without_any_ad_code_unchanged(self):
        files = package(guard=None)
        self.assertFalse(ad_regression.needs_regression(files))
        self.assertEqual(a1(files), [])


if __name__ == '__main__':
    unittest.main()
