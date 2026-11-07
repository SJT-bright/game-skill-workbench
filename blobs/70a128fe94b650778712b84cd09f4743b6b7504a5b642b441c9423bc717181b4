"""Consumer omissions, Cocos versions, ambiguity and read-only boundary regressions."""
import base64
from contextlib import redirect_stdout, redirect_stderr
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from art_consumer_index import inspect, main, compress

A = '12345678-90ab-cdef-1234-567890abcdef'
B = '24681357-aaaa-bbbb-cccc-111122223333'
C = 'abcde123-4567-8901-2345-6789abcdef01'
D = 'fafafafa-bbbb-1111-cccc-987654321012'


class ConsumerIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='consumer-index-')
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / 'project'
        (self.project / 'assets').mkdir(parents=True)

    def write(self, relative, value):
        p = self.project / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(value) if not isinstance(value, str) else value)
        return p

    def meta(self, relative, uuid, **extra):
        return self.write(relative + '.meta', dict(uuid=uuid, **extra))

    def asset(self, relative='assets/resources/rune/amber.png', uuid=A, **extra):
        self.write(relative, 'original image bytes, this tool does not decode artwork')
        self.meta(relative, uuid, **extra)
        return relative

    def reasons(self, report):
        return {x['reason'] for x in report['unresolved']}

    def test_cocos3_submeta_node_pointer_and_nested_parent(self):
        target = self.asset(subMetas={'frame': {'uuid': A + '@f9941', 'subMetas': {}}})
        doc = [{'__type__': 'cc.Prefab'}, {'__type__': 'cc.Node', '_name': 'UnseenPanel'},
               {'__type__': 'cc.Node', '_name': 'NestedGlyph', '_parent': {'__id__': 1}},
               {'__type__': 'cc.Sprite', 'node': {'__id__': 2}, '_enabled': False,
                '_spriteFrame': {'__uuid__': A + '@f9941'}}]
        self.write('assets/ui/quasar.prefab', doc)
        self.meta('assets/ui/quasar.prefab', B)
        self.write('assets/ui/saturn.scene', [{'asset': {'__uuid__': B}}])
        self.meta('assets/ui/saturn.scene', C)
        # Same base, undeclared different subasset must not be guessed as this image frame.
        self.write('assets/ui/decoy.json', {'frame': {'__uuid__': A + '@other'}})
        r = inspect(self.project, [target])
        a = r['assets'][0]
        self.assertEqual(len(a['direct']), 1)
        self.assertEqual(a['direct'][0]['json_pointer'], '/3/_spriteFrame/__uuid__')
        self.assertEqual(a['direct'][0]['node_path'], 'UnseenPanel/NestedGlyph')
        self.assertFalse(a['direct'][0]['serialized_enabled'])
        self.assertEqual(a['indirect'][0]['file'], 'assets/ui/saturn.scene')
        self.assertEqual(a['indirect'][0]['depth'], 2)
        self.assertIn('unmapped_uuid', self.reasons(r))

    def test_cocos2_compressed_frame_script_and_three_hop_parent(self):
        target = self.asset(uuid=A, subMetas={'oddFrame': {'uuid': D}})
        h = D.replace('-', '')
        encoded22 = h[:2] + base64.b64encode(bytes.fromhex(h[2:])).decode()
        self.write('assets/ui/larch.prefab', [
            {'__type__': 'cc.Node', '_name': 'Larch'},
            {'__type__': 'cc.Sprite', 'node': {'__id__': 0}, 'frame': {'__uuid__': encoded22}},
            {'__type__': compress(B), 'node': {'__id__': 0}}])
        self.meta('assets/ui/larch.prefab', C)
        self.write('assets/code/Orbit.ts', "cc.resources.load('rune/amber', cc.SpriteFrame, done);")
        self.meta('assets/code/Orbit.ts', B)
        self.write('assets/world/venue.fire', [{'nested': {'__uuid__': C}}])
        self.meta('assets/world/venue.fire', '00000000-1111-2222-3333-444444444444')
        r = inspect(self.project, [target])['assets'][0]
        self.assertEqual({x['file'] for x in r['direct']}, {'assets/ui/larch.prefab', 'assets/code/Orbit.ts'})
        self.assertIn('assets/world/venue.fire', {x['file'] for x in r['indirect']})
        # Remove direct frame; the script UUID chain is still sufficient to discover both parents.
        self.write('assets/ui/larch.prefab', [{'__type__': compress(B)}])
        r = inspect(self.project, [target])['assets'][0]
        parents = {x['file']: x['depth'] for x in r['indirect']}
        self.assertEqual(parents, {'assets/ui/larch.prefab': 2, 'assets/world/venue.fire': 3})

    def test_only_exact_literals_not_comments_or_similar_names(self):
        target = self.asset()
        self.write('assets/code/False.ts', '''// cc.resources.load('rune/amber');
/* 'rune/amber' */ const other = 'rune/amber2'; const name = 'amber';''')
        self.write('assets/code/Right.ts', "const path = 'rune/amber'; // review, not a proved load")
        self.write('assets/declared.json', {'binding': 'assets/resources/rune/amber.png'})
        r = inspect(self.project, [target])['assets'][0]
        self.assertEqual({x['file'] for x in r['direct']}, {'assets/code/Right.ts', 'assets/declared.json'})
        self.assertEqual({x['kind'] for x in r['direct']}, {'path_literal_review'})

    def test_dynamic_loads_interpolation_escape_and_external_remain_unresolved(self):
        target = self.asset()
        self.write('assets/code/Unknown.js', r'''resources.load(name);
resources.load('rune/' + item); resources.load(`rune/${item}`);
resources.load('rune\u002famber'); assetManager.loadRemote('https://example.test/a.png');''')
        r = inspect(self.project, [target])
        self.assertFalse(r['assets'][0]['direct'])
        self.assertTrue({'dynamic_load_unresolved', 'escaped_or_interpolated_literal', 'external_reference'} <= self.reasons(r))
        self.assertFalse(r['coverage_complete'])
        self.assertFalse(r['may_reduce_capture'])
        self.assertIsNone(r['visual_passed'])

    def test_ambiguous_resource_names_report_both_not_unique_match(self):
        target = self.asset()
        second = self.asset('assets/other/resources/rune/amber.png', B)
        self.write('assets/code/Maybe.ts', "resources.load('rune/amber');")
        r = inspect(self.project, [target, second])
        ambiguity = [x for x in r['unresolved'] if x['reason'] == 'ambiguous_reference']
        self.assertEqual(len(ambiguity), 1)
        self.assertEqual(set(ambiguity[0]['candidates']), {target, second})
        self.assertTrue(all(len(x['direct']) == 1 for x in r['assets']))

    def test_font_target_and_corrupt_inputs_do_not_disappear(self):
        target = self.asset('assets/resources/font/nova.fnt')
        (self.project / (target + '.meta')).unlink()
        self.write('assets/ui/bad.prefab', '{"broken"')
        self.write('assets/ui/other.prefab.meta', 'null')
        bad = self.write('assets/code/bad.ts', 'x')
        bad.write_bytes(b'\xff\xfe')
        self.write('assets/ui/direct.json', {'font': 'font/nova'})
        r = inspect(self.project, [target])
        self.assertTrue({'missing_meta_or_identity', 'bad_serialized_file', 'bad_meta', 'bad_text_encoding'} <= self.reasons(r))
        self.assertEqual(r['assets'][0]['direct'][0]['file'], 'assets/ui/direct.json')

    def test_nonstandard_scene_and_orphan_meta_remain_visible(self):
        target = self.asset()
        self.write('assets/unfamiliar.scene', {'new-schema': [{'__uuid__': A}]})
        self.meta('assets/absent.prefab', B)
        r = inspect(self.project, [target])
        self.assertTrue({'nonstandard_scene_serialization', 'orphan_meta'} <= self.reasons(r))
        hit = r['assets'][0]['direct'][0]
        self.assertIsNone(hit['node_path'])
        self.assertEqual(hit['json_pointer'], '/new-schema/0/__uuid__')

    def test_cycle_terminates_and_source_sha_binds_snapshot(self):
        target = self.asset()
        self.write('assets/a.prefab', {'frame': {'__uuid__': A}, 'sibling': {'__uuid__': C}})
        self.meta('assets/a.prefab', B)
        self.write('assets/b.prefab', {'sibling': {'__uuid__': B}})
        self.meta('assets/b.prefab', C)
        r = inspect(self.project, [target])
        self.assertEqual(len(r['assets'][0]['indirect']), 1)
        source = self.project / 'assets/a.prefab'
        self.assertEqual(r['assets'][0]['direct'][0]['source_sha256'], hashlib.sha256(source.read_bytes()).hexdigest())

    def test_symlink_outside_project_is_not_read(self):
        target = self.asset()
        outside = Path(self.temp.name) / 'secret'
        outside.mkdir()
        (outside / 'fake.prefab').write_text(json.dumps({'__uuid__': A}))
        (self.project / 'assets/linked').symlink_to(outside, target_is_directory=True)
        r = inspect(self.project, [target])
        self.assertFalse(r['assets'][0]['direct'])
        self.assertIn('symlink_directory_not_followed', self.reasons(r))

    def test_cli_cannot_write_project_and_inventory_does_not_mutate_inputs(self):
        target = self.asset()
        self.write('assets/inside.json', {'__uuid__': A})
        before = {str(p): p.read_bytes() for p in self.project.rglob('*') if p.is_file()}
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main(['--project', str(self.project), '--asset', target, '--out', str(self.project/'bad.json')]), 2)
            out = Path(self.temp.name) / 'report.json'
            self.assertEqual(main(['--project', str(self.project), '--asset', target, '--out', str(out)]), 0)
        self.assertFalse(json.loads(out.read_text())['coverage_complete'])
        after = {str(p): p.read_bytes() for p in self.project.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        with self.assertRaises(ValueError):
            inspect(self.project, ['../elsewhere.png'])
        with self.assertRaises(ValueError):
            inspect(self.project, [])


if __name__ == '__main__':
    unittest.main()
