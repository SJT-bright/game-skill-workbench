"""Portable identity/anti-mutation controls only; no renderer, game, CLI or upload."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest

# Each child imports the copied installation, so check_ledger retains its actual
# special-file identity rule even when the Skill root moves to another machine.
WORKER = r'''
from pathlib import Path
import hashlib,importlib,json,re,sys
from unittest.mock import patch
root=Path(sys.argv[1]).resolve();sys.path.insert(0,str(root));import startup_tool_identity as H
manifest=json.loads((root/'startup_tool_projection.json').read_bytes());group=manifest['groups']['scoped'];seeds=[root/n for n in group['seeds']]
scenario=sys.argv[2];home=Path(sys.argv[3]);native=home/'Native';project=home/'Project';native.mkdir();project.mkdir()
engine_name='cocos/cocos2d-js.js'
if scenario=='hashed-engine2':engine_name='cocos/cocos2d-js-min.a1b2c3d4.js'
if scenario=='engine3':engine_name='cocos-js/_virtual_cc-a1b2c3d4.js'
p=native/engine_name;p.parent.mkdir(parents=True);p.write_bytes(b'identity-only engine fixture')
proof={'schema':'native_startup_renderer.v1','producer':'real_browser_native_entry','binding':{k:'identity-fixture' for k in ('source_sha256','native_tree_sha256','web_tree_sha256','build_tag')},'inputs':[{'relative_path':engine_name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}]}
if scenario=='no-context':proof=None
if scenario=='no-engine':proof['inputs']=[]
if scenario=='creator1-root':(native/'cocos2d-js-min.js').write_bytes(b'excluded Creator1 shape')
if scenario=='creator1-marker':(project/'docs/checks').mkdir(parents=True);(project/'docs/checks/creator1-compatibility.json').write_text('{}')
if scenario=='wrong-engine-bytes':p.write_bytes(b'changed')
changed=None;original=None
mutations={'validator':'audit_startup_contract.py','new-import':'audit_startup_contract.py','guard':'preparation_scope_policy.json','engine-recognizer':'cocos1_compat.py','manifest':'startup_tool_projection.json','baseline':manifest['projections']['verify_native_zip.py']['source'],'helper':'startup_tool_identity.py','caller':'startup_scoped_evidence.py'}
if scenario in mutations:
 changed=root/mutations[scenario];original=changed.read_bytes();changed.write_bytes(original+(b'\nimport unreviewed_startup_helper\n' if scenario=='new-import' else b'\n# unreviewed identity change\n'))
 if scenario=='new-import':(root/'unreviewed_startup_helper.py').write_text('VALUE=True\n')
if scenario=='paired-helper-seal':
 changed=root/'startup_tool_identity.py';original=changed.read_bytes();changed.write_bytes(original+b'\n# unknown helper revision\n');new=hashlib.sha256(changed.read_bytes()).hexdigest().encode()
 for name in ('startup_scoped_evidence.py','native_startup_ledger.py'):
  caller=root/name;caller.write_bytes(re.sub(rb"^_STARTUP_TOOL_IDENTITY_SHA256 = '[0-9a-f]{64}'$",b"_STARTUP_TOOL_IDENTITY_SHA256 = '"+new+b"'",caller.read_bytes(),flags=re.M))
if scenario=='linked-baseline':
 changed=root/manifest['projections']['verify_native_zip.py']['source'];original=changed.read_bytes();target=home/'original-baseline.py';target.write_bytes(original);changed.unlink();changed.symlink_to(target)
read=Path.read_bytes;fired=[False]
races={'race-guard':'preparation_scope_policy.json','race-baseline':manifest['projections']['verify_native_zip.py']['source'],'race-helper':'startup_tool_identity.py'}
def racing(path):
 data=read(path)
 if scenario in races and path==root/races[scenario] and not fired[0]:
  fired[0]=True;path.write_bytes(data+b'\n# changed after first read\n')
 return data
with patch.object(Path,'read_bytes',racing):value=H.fingerprint(seeds,proof=proof,native=native,project=project)
expected=scenario in ('unchanged','hashed-engine2','engine3')
print(json.dumps({'scenario':scenario,'passed':(value==group['fingerprint'])==expected,'projected':value==group['fingerprint'],'expected_projected':expected,'race_fired':fired[0]}))
'''


class StartupToolIdentity(unittest.TestCase):
    def test_reviewed_startup_only_and_fail_closed(self):
        scripts=Path(__file__).resolve().parent
        scenarios=('unchanged','hashed-engine2','engine3','no-context','no-engine','creator1-root','creator1-marker','wrong-engine-bytes','validator','new-import','guard','engine-recognizer','manifest','baseline','helper','caller','paired-helper-seal','linked-baseline','race-guard','race-baseline','race-helper')
        with tempfile.TemporaryDirectory(prefix='startup identity 中文 ') as tmp:
            home=Path(tmp);template=home/'moved Skill 工具';template.mkdir()
            doc=json.loads((scripts/'startup_tool_projection.json').read_bytes())
            names=set(doc['groups']['scoped']['entries'])|set(doc['guards'])|{'startup_tool_identity.py','startup_tool_projection.json'}
            names|={v['source'] for v in doc['projections'].values()}
            # Also copy actual new imports, so raw fallback is the real current
            # closure rather than an artificial missing-import shortcut.
            for path in scripts.rglob('*.py'):
                if '__pycache__' not in path.parts:names.add(path.relative_to(scripts).as_posix())
            for name in names:
                src=scripts/name;dst=template/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(src.read_bytes())
            results=[]
            for scenario in scenarios:
                case=home/scenario;case.mkdir();root=case/'Skill 安装';shutil.copytree(template,root)
                run=subprocess.run([sys.executable,'-B','-c',WORKER,str(root),scenario,str(case)],capture_output=True,text=True,timeout=30)
                self.assertEqual(run.returncode,0,run.stderr)
                data=json.loads(run.stdout);results.append(data);self.assertTrue(data['passed'],data)
                if scenario.startswith('race-'):self.assertTrue(data['race_fired'],data)
            print(json.dumps({'schema':'startup_tool_identity_controls.v1','passed':True,'controls':results,'boundary':'Identity-only synthetic tool fixtures; no renderer/game/platform validation.'},ensure_ascii=False))


if __name__=='__main__':unittest.main()
