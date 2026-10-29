#!/usr/bin/env python3
"""Cocos2 relocated nativeBase risk + exact-bound runtime request evidence.
Static ZIP path safety does not validate paths produced by the asset pipeline.
"""
import argparse, hashlib, json, posixpath
from pathlib import Path

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def inventory(root):
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted(root.rglob('*')) if p.is_file()}
def canonical(url):
    return bool(url) and not url.startswith('/') and '\\' not in url and all(x not in ('', '.', '..') for x in url.split('/'))
def audit(native, proof=None):
    native=Path(native).resolve(); files=inventory(native); risks=[]; errors=[]
    configs=set(native.glob('assets/*/config.json')) | set(native.glob('subpackages/**/config.json'))
    for config in sorted(configs):
        data=json.loads(config.read_text()); base=config.parent.relative_to(native).as_posix()
        for key in ('nativeBase','importBase'):
            value=data.get(key)
            if not isinstance(value,str) or '://' in value: continue
            joined=base+'/'+value
            if not canonical(joined): risks.append({'config':config.relative_to(native).as_posix(),'field':key,'raw':joined,'resolved':posixpath.normpath(joined)})
    if risks:
        if proof is None: errors.append('Relocated Cocos paths need current final-request and two-ratio real scene Retry evidence; ZIP CRC is insufficient')
        else:
            proof=Path(proof).resolve()
            try:
                d=json.loads(proof.read_text())
                if d.get('schema')!='native_resource_paths_runtime.v1' or d.get('native_files')!=files: errors.append('Runtime request evidence schema or Native fingerprint is stale')
                refs=d.get('raw_evidence',[])
                if not refs: errors.append('Raw runtime evidence missing')
                for r in refs:
                    f=(proof.parent/r['path']).resolve()
                    if not f.is_relative_to(proof.parent) or not f.is_file() or sha(f)!=r.get('sha256'): errors.append('Raw runtime evidence missing/changed')
                requests=d.get('requests',[])
                if not requests: errors.append('Capture actual final Native SDK request paths, not config guesses')
                for r in requests:
                    path=r.get('final_path',''); indexes=r.get('evidence_refs',[])
                    if not canonical(path) or path not in files or r.get('success') is not True: errors.append('Noncanonical, missing or failed runtime resource: '+str(path))
                    if not indexes or any(type(i) is not int or not 0<=i<len(refs) for i in indexes): errors.append('Request raw evidence refs missing')
                for risk in risks:
                    if not any(r.get('raw_path','').startswith(risk['raw'].rstrip('/')+'/') and r.get('final_path','').startswith(risk['resolved'].rstrip('/')+'/') for r in requests): errors.append('No actual request trace for risky bundle path: '+risk['raw'])
                calibration=d.get('calibration_evidence_refs',[])
                if not calibration or any(type(i) is not int or not 0<=i<len(refs) for i in calibration): errors.append('Old failure calibration raw evidence refs missing')
                rows=d.get('scene_retry',[])
                ratios=set()
                for r in rows:
                    vp=r.get('viewport',[])
                    if len(vp)==2 and all(type(v) is int and v>0 for v in vp): ratios.add(round(vp[0]/vp[1],3))
                    for k in ('actual_scene_failure','single_trusted_retry','fresh_resource_request','home_presented','play_entered','gameplay_input_changed','extracted_native'):
                        if r.get(k) is not True: errors.append('Scene Retry missing '+k)
                    ix=r.get('evidence_refs',[])
                    if not ix or any(type(i) is not int or not 0<=i<len(refs) for i in ix): errors.append('Scene Retry raw evidence refs missing')
                if len(ratios)<2: errors.append('Two actual phone ratios required after ZIP extraction')
                if d.get('old_same_boundary_failed') is not True: errors.append('Old same-boundary failure calibration missing')
                if d.get('strict_filesystem') is not True: errors.append('Filesystem must check real files and preserve errors; no unconditional access success')
            except (OSError,ValueError,KeyError,TypeError) as e: errors.append('Invalid runtime evidence: '+str(e))
    return {'tool':'audit_native_resource_paths','status':'blocked' if errors else 'pass','risks':risks,'errors':errors,'native_files':files,'limits':'Detects relocated Cocos2 config paths and validates supplied byte-bound evidence; human review of raw traces still required. Does not prove real iPhone/TikTok success.'}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--native',type=Path,required=True);p.add_argument('--proof',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    try: r=audit(a.native,a.proof)
    except (OSError,ValueError,TypeError) as e:r={'tool':'audit_native_resource_paths','status':'blocked','errors':[str(e)]}
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:r[k] for k in ['status','errors']}));raise SystemExit(0 if r['status']=='pass' else 2)
