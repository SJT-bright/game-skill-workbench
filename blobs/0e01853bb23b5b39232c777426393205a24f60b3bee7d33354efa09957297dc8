"""Synthetic contracts for byte-bound pre-download audio resolvers; no game runner.

The fixture's reviewed fingerprints are registered only inside each test. Startup
syntax/dependency closure is the actual production audit, with no patched result.
"""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import audit_packed_assets as assets


OLD = 'subpackages/resources/native/aa/clip.mp3'
TARGET = 'subpackages/audio/native/aa/clip.mp3'
ENTRY = "require('./adapter.js');globalThis.fixtureReady=true;"
ADAPTER = '''var AUDIO_BUNDLE_MAP = {"subpackages/resources/native/aa/clip.mp3":"subpackages/audio/native/aa/clip.mp3"};
var audioBundleReady=false;
function prepareAudioBundle(done){tt.loadSubpackage({name:'audio',success:function(){audioBundleReady=true;done();},fail:done});}
function downloadAsset(url, options, onComplete) {
 if(AUDIO_BUNDLE_MAP[url]){prepareAudioBundle(function(error){if(error){onComplete(error);return;}download(AUDIO_BUNDLE_MAP[url],doNothing,options,options.onFileProgress,onComplete);});return;}
 download(url,doNothing,options,options.onFileProgress,onComplete);
}
cc.assetManager.downloader.register({'.mp3':downloadAsset});
'''


class AudioAliasTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='packed audio alias ')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.write('game.js', ENTRY)
        self.write('game.json', json.dumps({'subpackages': [{'name': 'audio', 'root': 'subpackages/audio/'}]}))
        self.write('project.config.json', '{}')
        self.write('subpackages/audio/game.js', 'globalThis.audioFixture=true;')
        self.write('adapter.js', ADAPTER)
        self.write(TARGET, 'audio fixture bytes')

    def write(self, name, source):
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source)
        return target

    def registered(self, source=ADAPTER, entry=ENTRY):
        # Trust calibration, not an audit mock: the registered exact fixture is
        # executable JS; every source/entry/target/dependency check remains real.
        return patch.dict(assets._AUDIO_RESOLVERS, {
            hashlib.sha256(source.encode()).hexdigest(): {
                'source_path': 'adapter.js', 'entry_sha256': hashlib.sha256(entry.encode()).hexdigest(),
                'bundle': 'audio', 'bundle_root': 'subpackages/audio',
            }
        })

    def check(self, expected):
        result = assets.audit(self.root)
        self.assertIs(result['passed'], expected, result)
        return result

    def test_known_resolver_has_real_target_and_actual_startup_closure(self):
        with self.registered():
            result = self.check(True)
        refs = [row for row in result['literal_references'] if row['path'] == OLD]
        self.assertEqual([row['resolved_path'] for row in refs], [TARGET])

    def test_unknown_protocol_retains_original_required_file(self):
        self.check(False)

    def test_comment_labels_do_not_resolve_a_missing_file(self):
        source = '/* ' + ADAPTER + ' */\nconst real=' + json.dumps(OLD) + ';'
        self.write('adapter.js', source)
        with self.registered():
            self.check(False)

    def test_dead_branch_does_not_inherit_another_fingerprint(self):
        self.write('adapter.js', 'if(false){' + ADAPTER + '}')
        with self.registered():
            self.check(False)

    def test_throwing_consumer_does_not_inherit_another_fingerprint(self):
        self.write('adapter.js', ADAPTER.replace('prepareAudioBundle(function(error)', "(()=>{throw Error('broken')})(function(error)"))
        with self.registered():
            self.check(False)

    def test_missing_actual_mapped_file_refuses(self):
        (self.root / TARGET).unlink()
        with self.registered():
            self.check(False)

    def test_changed_mapping_to_another_existing_file_refuses(self):
        self.write('subpackages/audio/native/aa/other.mp3', 'unrelated')
        self.write('adapter.js', ADAPTER.replace(TARGET, 'subpackages/audio/native/aa/other.mp3'))
        with self.registered():
            self.check(False)

    def test_entry_comment_or_unreachable_require_is_not_registered_entry(self):
        self.write('game.js', 'if(false){' + ENTRY + '}')
        with self.registered():
            self.check(False)

    def test_missing_subpackage_entry_is_real_closure_failure(self):
        (self.root / 'subpackages/audio/game.js').unlink()
        with self.registered():
            result = self.check(False)
        self.assertTrue(any('startup closure' in row for row in result['errors']), result)

    def test_transitive_module_missing_is_real_closure_failure(self):
        source = "require('./dependency.js');\n" + ADAPTER
        self.write('adapter.js', source)
        self.write('dependency.js', "require('./missing-deeper.js');")
        with self.registered(source):
            result = self.check(False)
            self.assertTrue(any('missing-deeper' in row for row in result['errors']), result)
            self.write('missing-deeper.js', 'globalThis.fixtureDependency=true;')
            self.check(True)

    def test_same_bytes_in_unrelated_source_path_do_not_resolve(self):
        self.write('unrelated.js', ADAPTER)
        self.write('adapter.js', '// actual adapter has no resolver')
        with self.registered():
            self.check(False)

    def test_incorrect_subpackage_declaration_refuses(self):
        self.write('game.json', json.dumps({'subpackages': [{'name': 'audio', 'root': 'subpackages/other/'}]}))
        with self.registered():
            self.check(False)

    def test_registered_unsafe_target_still_refuses(self):
        source = ADAPTER.replace(TARGET, 'subpackages/audio/../../outside.mp3')
        self.write('adapter.js', source)
        with self.registered(source):
            self.check(False)

    def test_registered_duplicate_mapping_still_refuses(self):
        source = ADAPTER.replace(json.dumps(OLD) + ':', json.dumps(OLD) + ':' + json.dumps(TARGET) + ',' + json.dumps(OLD) + ':')
        self.write('adapter.js', source)
        with self.registered(source):
            result = self.check(False)
        self.assertTrue(any('duplicate JSON key' in row for row in result['errors']), result)

    def test_registered_target_cannot_follow_a_symlink_outside_the_package(self):
        target = self.root / TARGET
        target.unlink()
        target.symlink_to('/dev/null')
        with self.registered():
            self.check(False)

    def test_original_existing_assets_remain_valid_without_any_resolver(self):
        self.write('adapter.js', 'const ordinary=' + json.dumps(OLD) + ';')
        self.write(OLD, 'original exists')
        self.check(True)


if __name__ == '__main__':
    unittest.main()
