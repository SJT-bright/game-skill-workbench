"""Final ZIP partition boundaries and fresh delivery receipts; no browser/CI."""
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from upload_size_gate import enforce, inspect_files, inspect_zip


def payload():
    return {'game.js':b'boot();', 'game.json':json.dumps({'subpackages':[{'name':'res','root':'subpackages/res'}]}).encode(),
            'project.config.json':b'{"appid":"test"}',
            'src/settings.json':b'{"subpackages":["res"],"bundleVers":{}}',
            'subpackages/res/game.js':b'load();', 'subpackages/res/config.json':b'{"name":"res"}',
            'subpackages/res/native/image.png':b'image'}


class SizeGate(unittest.TestCase):
    def test_main_exact_boundary_then_over(self):
        self.assertEqual(enforce({'game.js':4_000_000},{})['main_bytes'],4_000_000)
        with self.assertRaisesRegex(ValueError,'main package'):
            enforce({'game.js':4_000_001},{})

    def test_normal_subpackage_and_total_boundary(self):
        g={'subpackages':[{'name':'res','root':'subpackages/res'}]}
        r=enforce({'game.js':1,'subpackages/res/file':29_999_999},g)
        self.assertEqual((r['main_bytes'],r['total_bytes']),(1,30_000_000))
        with self.assertRaisesRegex(ValueError,'total package'):
            enforce({'game.js':2,'subpackages/res/file':29_999_999},g)

    def test_independent_boundary_then_over(self):
        g={'subpackages':[{'name':'res','root':'subpackages/res','independent':True}]}
        enforce({'subpackages/res/file':4_000_000},g)
        with self.assertRaisesRegex(ValueError,'Independent'):
            enforce({'subpackages/res/file':4_000_001},g)

    def test_wrong_case_is_not_silently_ignored(self):
        for key in ('subPackages','SubPackages'):
            with self.assertRaisesRegex(ValueError,'wrong/ambiguous'):
                enforce({'subpackages/res/file':1},{key:[]})

    def test_nested_duplicate_empty_and_case_mismatched_roots(self):
        for rows in ([{'name':'x','root':'missing'}],
                     [{'name':'x','root':'subpackages/res'},{'name':'y','root':'subpackages/res/nested'}],
                     [{'name':'x','root':'subpackages/res'},{'name':'x','root':'other'}],
                     [{'name':'x','root':'Subpackages/res'}]):
            with self.assertRaises(ValueError):
                enforce({'subpackages/res/file':1,'subpackages/res/nested/file':1,'other/file':1},
                        {'subpackages':rows})

    def test_prefix_exclusion_is_directory_scoped(self):
        r=enforce({'res/file':1,'resources/file':12},{'subpackages':[{'name':'res','root':'res'}]})
        self.assertEqual(r['main_bytes'],12)

    def test_engine_bundle_configuration_required_and_version_selected(self):
        f=payload();inspect_files(f)
        del f['subpackages/res/config.json']
        with self.assertRaisesRegex(ValueError,'Missing Cocos'):
            inspect_files(f)
        f['src/settings.json']=b'{"subpackages":["res"],"bundleVers":{"res":"abc"}}'
        f['subpackages/res/config.abc.json']=b'{"name":"other"}'
        with self.assertRaisesRegex(ValueError,'name differs'):
            inspect_files(f)
        f['subpackages/res/config.abc.json']=b'{"name":"res"}'
        inspect_files(f)

    def test_custom_code_subpackage_is_allowed_but_engine_name_must_exist(self):
        f=payload();f['subpackages/custom/game.js']=b'code();'
        f['game.json']=b'{"subpackages":[{"name":"res","root":"subpackages/res"},{"name":"custom","root":"subpackages/custom"}]}'
        inspect_files(f)
        f['src/settings.json']=b'{"subpackages":["missing"]}'
        with self.assertRaisesRegex(ValueError,'do not match'):
            inspect_files(f)

    def test_duplicate_json_and_orphan_files_are_refused(self):
        f=payload();f['game.json']=b'{"subpackages":[],"subpackages":[]}'
        with self.assertRaisesRegex(ValueError,'Duplicate JSON'):
            inspect_files(f)
        f=payload();f['subpackages/forgotten/file']=b'x'
        with self.assertRaisesRegex(ValueError,'Unregistered'):
            inspect_files(f)

    def test_same_bytes_rechecked_renamed_and_known_rejection(self):
        with tempfile.TemporaryDirectory(prefix='upload-size-') as tmp:
            root=Path(tmp);p=root/'original.zip'
            with zipfile.ZipFile(p,'w') as z:
                for n,b in payload().items():z.writestr(n,b)
            a=inspect_zip(p);b=inspect_zip(p)
            self.assertTrue(a['passed']);self.assertTrue(b['passed'])
            self.assertNotEqual(a['run_id'],b['run_id']);self.assertEqual(a['sha256'],b['sha256'])
            q=root/'renamed.zip';q.write_bytes(p.read_bytes());c=inspect_zip(q)
            self.assertTrue(c['passed']);self.assertEqual(c['archive'],str(q.resolve()))
            feedback=root/'feedback.json'
            feedback.write_text(json.dumps({'platform':'tiktok','rejected_sha256':a['sha256']}))
            d=inspect_zip(q,feedback=feedback)
            self.assertFalse(d['passed']);self.assertIn('rejected',d['errors'][0])
            feedback.write_text(json.dumps({'platform':'tiktok','rejected_sha256':a['sha256'].upper()}))
            self.assertFalse(inspect_zip(q,feedback=feedback)['passed'])


if __name__=='__main__':
    unittest.main()
