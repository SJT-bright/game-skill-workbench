#!/usr/bin/env python3
"""Known prerequisite refusal only; renderer/device tests are separate."""
from pathlib import Path
import json,os,sys,tempfile,unittest
if os.environ.get('SKILL_TEST_DEPS'):sys.path.insert(1,os.environ['SKILL_TEST_DEPS'])
from audit_upload_startup import audit_adapter_preconditions
from package_gates.adapter_fix import apply

class AdapterTests(unittest.TestCase):
 def fixture(self):
  return {'game.js':b"require('adapter-min.js');",'game.json':b'{}','project.config.json':b'{}','cocos/cocos2d-js-min.js':b'cc.ENGINE_VERSION="2.4.15";',
   'adapter-min.js':b'''var u=tt.getSystemInfoSync();Number.parseInt(u.SDKVersion[0])<2;u.isSubContext=void 0===tt.getOpenDataContext;function A(t,e,n){c(t,function(e){e?n(null,t):n(new Error("file ".concat(t," does not exist!")))})}'''}
 def test_old_artifact_refused_and_shared_normalizer_repairs(self):
  files=self.fixture();r=audit_adapter_preconditions(files);self.assertFalse(r['passed']);self.assertEqual(set(r['known_unsafe']),{'sdk_version','sub_context','pkg_fs_access'})
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   for name,data in files.items():p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
   fixed=apply(root);self.assertFalse(fixed['blocks']);self.assertEqual(len(fixed['changed']),3)
   self.assertTrue(audit_adapter_preconditions({n:(root/n).read_bytes() for n in files})['passed'])
 def test_renaming_does_not_change_adapter_semantics(self):
  files=self.fixture();files['project.config.json']=b'{"projectname":"renamed-ios-fixed"}'
  self.assertFalse(audit_adapter_preconditions(files)['passed'])
 def test_cocos3_not_misclassified_as_cocos2(self):
  files=self.fixture();files['cocos/cocos2d-js-min.js']=b'cc.ENGINE_VERSION="3.8.8";';r=audit_adapter_preconditions(files);self.assertTrue(r['passed']);self.assertEqual(r['target'],[])

if __name__=='__main__':unittest.main(verbosity=2)
