#!/usr/bin/env python3
"""Check recorded hint duplication; validates captures, not runtime authenticity."""
import argparse, collections, hashlib, json, math, re
from pathlib import Path

ROLES = ('persistent_hint', 'transient_hint')
def number(x):
 return type(x) in (int, float) and math.isfinite(x)
def visible(m):
 return m.get('visible') is not False and number(m.get('opacity')) and m['opacity'] > .01

def duplicates(messages):
 counts = collections.Counter(m.get('key') for m in messages if isinstance(m,dict) and m.get('role') in ROLES and visible(m))
 return sorted(k for k,v in counts.items() if isinstance(k,str) and v>1)

def check(data, base=None):
 errors=[];base=Path(base or '.')
 if not isinstance(data,dict) or data.get('producer')!='real_cocos_hint_presentations' or not isinstance(data.get('cases'),list) or not data['cases']:
  return ['missing_runtime_cases']
 ids=set()
 for case in data['cases']:
  if not isinstance(case,dict) or not isinstance(case.get('id'),str) or not case['id']:
   errors.append('invalid_case');continue
  cid=case['id']
  if cid in ids:errors.append(cid+':duplicate_case')
  ids.add(cid);samples=case.get('samples');timing=case.get('timing');settled=case.get('settled_expected','present')
  if settled not in ('present','absent'):errors.append(cid+':invalid_settled_expectation')
  if not isinstance(timing,dict):timing={}
  early=timing.get('appearance_max_ms');late=timing.get('settled_min_ms')
  timing_ok=number(early) and number(late) and 0<early<late
  if not timing_ok:errors.append(cid+':missing_timing_contract')
  if not isinstance(samples,list) or len(samples)!=2 or any(not isinstance(s,dict) or s.get('stage') not in ('appearance','settled') for s in samples) or collections.Counter(s.get('stage') for s in samples)!=collections.Counter(['appearance','settled']):
   errors.append(cid+':missing_temporal_stage');continue
  bindings=[]
  for s in samples:
   prefix=cid+':'+s['stage']+':'
   shot=s.get('screenshot');sha=s.get('screenshot_sha256');bundle=s.get('bundle_sha256');key=s.get('expected_hint')
   if not isinstance(shot,str) or not shot:
    errors.append(prefix+'invalid_screenshot')
   else:
    path=Path(shot);path=path if path.is_absolute() else base/path
    try:
     if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=sha:errors.append(prefix+'invalid_screenshot')
    except OSError:errors.append(prefix+'invalid_screenshot')
   if not isinstance(bundle,str) or not re.fullmatch('[0-9a-fA-F]{64}',bundle) or not isinstance(s.get('screen'),str) or not s['screen'] or not isinstance(key,str) or not key:
    errors.append(prefix+'missing_runtime_binding')
   bindings.append((bundle,s.get('screen'),key))
   elapsed=s.get('elapsed_ms')
   if not number(elapsed) or elapsed<0:errors.append(prefix+'invalid_elapsed')
   elif timing_ok:
    if s['stage']=='appearance' and elapsed>early:errors.append(prefix+'missed_appearance_window')
    if s['stage']=='settled' and elapsed<late:errors.append(prefix+'settled_too_early')
   messages=s.get('messages')
   if not isinstance(messages,list):errors.append(prefix+'invalid_messages');continue
   paths=set();valid=[]
   for m in messages:
    if not isinstance(m,dict) or not number(m.get('opacity')) or not 0<=m['opacity']<=1 or ('visible' in m and type(m['visible']) is not bool):
     errors.append(prefix+'invalid_message');continue
    if not visible(m):continue
    r=m.get('rect');node=m.get('path')
    if not isinstance(r,dict) or any(not number(r.get(k)) or r[k]<=0 for k in ('width','height')) or not isinstance(node,str) or not node:
     errors.append(prefix+'invalid_visible_geometry');continue
    if node in paths:errors.append(prefix+'duplicate_node')
    paths.add(node)
    if m.get('role') in ROLES and (not isinstance(m.get('key'),str) or not m['key']):errors.append(prefix+'missing_hint_key');continue
    valid.append(m)
   count=sum(m.get('key')==key and m.get('role') in ROLES for m in valid)
   if s['stage']=='appearance' or settled=='present':
    if not count:errors.append(prefix+'missing_expected_hint')
   elif settled=='absent' and count:errors.append(prefix+'hint_not_dismissed')
   errors.extend(prefix+'duplicate_hint:'+k for k in duplicates(valid))
  if bindings[0]!=bindings[1]:errors.append(cid+':inconsistent_runtime_binding')
 return errors

def selftest():
 p={'key':'instruction','role':'persistent_hint','opacity':1};t={**p,'role':'transient_hint'}
 assert duplicates([p,t])==['instruction']
 assert not duplicates([p,{**t,'key':'different_feedback'}])
 assert not duplicates([p,{**t,'opacity':0}])
 assert not duplicates([{'key':'buy','role':'button','opacity':1}]*2)
 assert duplicates([p,p])==['instruction']
 assert check({'producer':'real_cocos_hint_presentations','cases':[]})==['missing_runtime_cases']
 return 6

if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('capture',nargs='?',type=Path);ap.add_argument('--out',type=Path);ap.add_argument('--self-test',action='store_true');args=ap.parse_args()
 if args.self_test:print(json.dumps({'self_tests_passed':selftest()}));raise SystemExit(0)
 if not args.capture:ap.error('capture required')
 try:errors=check(json.loads(args.capture.read_text()),args.capture.resolve().parent)
 except (ValueError,OSError) as exc:errors=['invalid_capture:'+str(exc)]
 report={'input':str(args.capture.resolve()),'passed':not errors,'errors':errors}
 if args.out:args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(report,ensure_ascii=False));raise SystemExit(1 if errors else 0)
