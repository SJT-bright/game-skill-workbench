#!/usr/bin/env python3
"""Synthetic checker regressions only; never game/device acceptance."""
import copy,hashlib,json,subprocess,sys,tempfile
from pathlib import Path
from audit_native_resource_paths import audit,inventory
HERE=Path(__file__).resolve().parent
results=[]
def png1x1():
    # v7.7: finalize compresses every PNG in the build, so the fixture art must be a real PNG
    import struct,zlib
    chunk=lambda t,d:struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(b'\0\0\0\0\0'))+chunk(b'IEND',b'')
def check(name,condition):
    if not condition: raise AssertionError(name)
    results.append({'id':name,'pass':True})
with tempfile.TemporaryDirectory(prefix='native-path-gate ') as td:
    root=Path(td);native=root/'native';cfg=native/'assets/resources/config.json';cfg.parent.mkdir(parents=True)
    cfg.write_text(json.dumps({'nativeBase':'../../subpackages/core/native'}));asset=native/'subpackages/core/native/ab/a.png';asset.parent.mkdir(parents=True);asset.write_bytes(png1x1())
    raw=root/'raw.json';raw.write_text('{"fixture":"synthetic checker calibration, not gameplay"}')
    proof=root/'proof.json'
    d={'schema':'native_resource_paths_runtime.v1','native_files':inventory(native),'raw_evidence':[{'path':'raw.json','sha256':hashlib.sha256(raw.read_bytes()).hexdigest()}],'strict_filesystem':True,'old_same_boundary_failed':True,'calibration_evidence_refs':[0],
       'requests':[{'raw_path':'assets/resources/../../subpackages/core/native/ab/a.png','final_path':'subpackages/core/native/ab/a.png','success':True,'evidence_refs':[0]}],'scene_retry':[]}
    for vp in [[393,852],[412,915]]:
        row={k:True for k in ['actual_scene_failure','single_trusted_retry','fresh_resource_request','home_presented','play_entered','gameplay_input_changed','extracted_native']};row.update(viewport=vp,evidence_refs=[0]);d['scene_retry'].append(row)
    def run(value):proof.write_text(json.dumps(value));return audit(native,proof)['status']
    check('old-relocation-without-runtime-evidence-refused',audit(native)['status']=='blocked')
    check('well-formed-current-fixture-accepted-as-checker-input-only',run(d)=='pass')
    mutations=[('stale-native',lambda x:x.update(native_files={})),('missing-file',lambda x:x['requests'][0].update(final_path='subpackages/core/native/missing.png')),('uncanonical-final',lambda x:x['requests'][0].update(final_path='assets/../subpackages/core/native/ab/a.png')),('wrong-case',lambda x:x['requests'][0].update(final_path='subpackages/core/native/ab/A.png')),('stale-raw',lambda x:x['raw_evidence'][0].update(sha256='0'*64)),('one-ratio',lambda x:x['scene_retry'].pop()),('no-real-input',lambda x:x['scene_retry'][0].update(gameplay_input_changed=False)),('not-extracted',lambda x:x['scene_retry'][0].update(extracted_native=False)),('missing-calibration',lambda x:x.update(calibration_evidence_refs=[])),('uncovered-risk',lambda x:x['requests'][0].update(raw_path='other/a.png'))]
    for name,change in mutations:
        bad=copy.deepcopy(d);change(bad);check(name+'-refused',run(bad)=='blocked')
    review=root/'review.json';review.write_text('{}');out=root/'must-not-exist.zip'
    # v7.7: the writer checks the source record (K5) and runs tiktok_finalize before this check, so the fixture is a
    # finalized 2.4 project and a 2.4 build (test_tiktok_finalize fixtures) with a numeric App ID.
    import tiktok_finalize as F, test_tiktok_finalize as H
    H.build24(native);project=H.project24(root/'project')
    kitcfg=(HERE.parent/'assets/platform-kit/assets/tiktok-platform/PlatformConfig.js').read_text(encoding='utf-8')
    (project/'assets/tiktok-platform/PlatformConfig.js').write_text(kitcfg.replace("gameId: 'change-me'","gameId: 'fixture'").replace('normalLevelCoins: 0,','normalLevelCoins: 12,'),encoding='utf-8')
    check('fixture-source-finalized',F.finalize_source(project,'remake')['blocks']==[])
    command=[sys.executable,str(HERE/'make_tiktok_zip.py'),'--native',str(native),'--app-id',H.APP,'--out',str(out),'--project',str(project),'--web',str(native),'--build-tag','fixture','--review',str(review)]
    r=subprocess.run(command,capture_output=True,text=True)
    check('actual-formal-writer-refuses-before-zip',r.returncode!=0 and not out.exists() and 'native resource path check' in r.stderr+r.stdout)
    cfg.write_text(json.dumps({'nativeBase':'native'}));check('normal-unrelocated-control',audit(native)['status']=='pass')
    sub=native/'subpackages/second/config.json';sub.parent.mkdir(parents=True);sub.write_text(json.dumps({'nativeBase':'../../other/native'}))
    check('subpackage-relocated-config-without-evidence-refused',audit(native)['status']=='blocked')
    sub.write_text(json.dumps({'nativeBase':'native'}));check('subpackage-normal-control',audit(native)['status']=='pass')
print(json.dumps({'status':'pass','scope':'synthetic checker and actual writer refusal only, no game/phone acceptance','cases':results},indent=2))
