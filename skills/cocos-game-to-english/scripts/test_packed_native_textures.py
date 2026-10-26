import json,tempfile,unittest
from pathlib import Path
from audit_packed_assets import audit
class PackedNativeTextureTests(unittest.TestCase):
 def fixture(self,root,extension='0',native_base='native'):
  base=root/'subpackages/art';(base/'import/ab').mkdir(parents=True)
  (base/'config.json').write_text(json.dumps({'uuids':['00AAAAAAAAAAAAAAAAAAAA'],'packs':{'ab123':[0]},'nativeBase':native_base,'importBase':'import'}))
  (base/'import/ab/ab123.json').write_text(json.dumps({'type':'cc.Texture2D','data':extension+',9729,9729,33071,33071,0,0,1'}))
  target=base/'native/00/00000000-0000-0000-0000-000000000000.png';target.parent.mkdir(parents=True);return target
 def test_existing_compact_uuid_texture(self):
  with tempfile.TemporaryDirectory()as d:
   p=Path(d);self.fixture(p).write_bytes(b'fixture');r=audit(p);self.assertTrue(r['passed'],r);self.assertEqual(len(r['native_texture_references']),1)
 def test_missing_texture_rejected(self):
  with tempfile.TemporaryDirectory()as d:
   p=Path(d);self.fixture(p);r=audit(p);self.assertFalse(r['passed']);self.assertTrue(any('missing Cocos packed native texture' in x for x in r['errors']))
 def test_advertised_second_format_missing_rejected(self):
  with tempfile.TemporaryDirectory()as d:
   p=Path(d);self.fixture(p,'0_4').write_bytes(b'fixture');r=audit(p);self.assertFalse(r['passed']);self.assertTrue(any('.webp' in x for x in r['errors']))
 def test_external_native_base_rejected(self):
  with tempfile.TemporaryDirectory()as d:
   p=Path(d);self.fixture(p,native_base='../../../../outside');r=audit(p);self.assertFalse(r['passed']);self.assertTrue(any('escapes package' in x for x in r['errors']))
if __name__=='__main__':unittest.main()
