"""Only pure AST results are reused; package checks and changed bytes remain live."""
import copy,shutil,subprocess,unittest
from unittest.mock import patch
import audit_upload_startup as audit

def fixture():
 return {'game.js':b"require('./a/x');require('./b/x');",'game.json':b'{}','project.config.json':b'{"appid":"test"}',
         'a/x.js':b"require('./leaf');",'b/x.js':b"require('./leaf');",'a/leaf.js':b'exports.ok=1;','b/leaf.js':b'exports.ok=1;'}
class ParseReuseTests(unittest.TestCase):
 def setUp(self):audit._PARSE_CACHE.clear();self.node=shutil.which('node');self.signature=audit.parser_fingerprint()
 def test_same_bytes_parse_once_and_return_independent_copy(self):
  original=subprocess.run
  with patch.object(audit.subprocess,'run',wraps=original) as run:
   a=audit.parse_package_source(b"require('./x')",self.node,self.signature);a[2]['dependencies'].clear()
   b=audit.parse_package_source(b"require('./x')",self.node,self.signature)
   self.assertEqual(run.call_count,1);self.assertTrue(b[3]);self.assertEqual(b[2]['dependencies'][0]['request'],'./x')
 def test_source_and_parser_or_vendor_fingerprint_invalidate(self):
  original=subprocess.run
  with patch.object(audit.subprocess,'run',wraps=original) as run:
   audit.parse_package_source(b'var a=1;',self.node,self.signature)
   audit.parse_package_source(b'var a=2;',self.node,self.signature)
   audit.parse_package_source(b'var a=1;',self.node,('new-parser',self.signature[1]))
   audit.parse_package_source(b'var a=1;',self.node,(self.signature[0],'new-acorn'))
   self.assertEqual(run.call_count,4)
 def test_parse_failure_not_reused_as_success(self):
  original=subprocess.run
  with patch.object(audit.subprocess,'run',wraps=original) as run:
   for _ in range(2):self.assertNotEqual(audit.parse_package_source(b'function {',self.node,self.signature)[0],0)
   self.assertEqual(run.call_count,2)
 def test_reused_ast_still_resolves_each_callers_current_paths(self):
  files=fixture();before=copy.deepcopy(files);a=audit.audit_files(files);self.assertTrue(a['passed'],a['errors']);self.assertEqual(files,before)
  self.assertGreater(a['js_parse_reuse']['cache_hits'],0)
  files.pop('b/leaf.js');b=audit.audit_files(files);self.assertFalse(b['passed']);self.assertTrue(any('b/leaf' in e for e in b['errors']))
 def test_whole_graph_rechecks_after_changed_source(self):
  files=fixture();self.assertTrue(audit.audit_files(files)['passed']);files['game.js']=b"require('./new-missing');"
  b=audit.audit_files(files);self.assertFalse(b['passed']);self.assertTrue(any('new-missing' in e for e in b['errors']))
 def test_missing_node_not_hidden_by_cached_ast(self):
  files=fixture();self.assertTrue(audit.audit_files(files)['passed'])
  with patch.object(audit.shutil,'which',return_value=None):b=audit.audit_files(files)
  self.assertFalse(b['passed']);self.assertTrue(any('Node.js required' in e for e in b['errors']))
if __name__=='__main__':unittest.main()
