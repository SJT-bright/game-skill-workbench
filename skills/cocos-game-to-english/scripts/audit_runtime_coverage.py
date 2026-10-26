#!/usr/bin/env python3
"""Bind persistence-site ownership and regression evidence to actual source/Web/Native bytes.
Discovery is conservative (literal/dynamic calls, not semantic proof). This audit never runs game code.
"""
import argparse,hashlib,json,re,sys
from pathlib import Path
CALL=re.compile(r'\b(getItem|setItem|removeItem|getStorageSync|setStorageSync|removeStorageSync)\s*\(\s*([^,;)\n]{0,180})')
SKIP={'node_modules','.git','library','temp','__pycache__'}
REQUIRED={'reward':{'missing_null','missing_empty_string','valid_legacy','malformed_preserved','read_failure','write_readback_failure','grant_consume_restart','old_failure_control','reachable_entry'},'progress':{'missing_empty_string','valid_legacy','read_failure','write_readback_failure','restart'},'settings':{'missing_empty_string','valid_legacy','restart'},'other':{'missing_empty_string','valid_legacy','read_failure','write_readback_failure','restart'}}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inventory(roots):
 files={};sites={}
 for label,root in roots.items():
  for p in sorted(root.rglob('*')):
   if not p.is_file() or p.suffix not in {'.js','.ts','.json'} or SKIP & set(p.relative_to(root).parts):continue
   rel=label+'/'+p.relative_to(root).as_posix();files[rel]=sha(p)
   if p.suffix=='.json':continue
   for i,m in enumerate(CALL.finditer(p.read_text(errors='replace'))):
    ident=rel+'#storage-'+str(i)
    sites[ident]={'file':rel,'call':m.group(1),'argument':m.group(2).strip()}
 return files,sites

def verify(doc,roots,base):
 files,sites=inventory(roots);errors=[]
 if any(not any(k.startswith(layer+'/') for k in files) for layer in roots):errors.append('every artifact layer needs nonempty source/config files')
 if doc.get('schema')!='runtime_coverage.v1':errors.append('missing runtime_coverage.v1 schema')
 if doc.get('artifacts')!=files:errors.append('source/Web/Native artifact fingerprint mismatch; rediscover and revalidate')
 rows=doc.get('sites',{});domains=doc.get('domains',{})
 if set(rows)!=set(sites):errors.append('missing or stale discovered storage sites')
 if not isinstance(domains,dict):return ['domains must be an object']
 for key,site in sites.items():
  row=rows.get(key,{})
  if row.get('discovered')!=site:errors.append(key+': discovery changed')
  owner=row.get('domain')
  if owner not in domains:errors.append(key+': no tested data-domain owner; engine/wrapper calls also need ownership or reasoned exclusion')
 def evidence(ref):
  if not isinstance(ref,dict) or not isinstance(ref.get('path'),str):return False
  p=(base/ref['path']).resolve()
  return p.is_file() and sha(p)==ref.get('sha256')
 for name,row in domains.items():
  kind=row.get('kind');owned=[k for k,v in rows.items() if v.get('domain')==name]
  if not owned:errors.append(name+': domain owns no discovered site')
  if kind=='excluded':
   if len(str(row.get('reason','')).strip())<30 or not evidence(row.get('evidence')):errors.append(name+': excluded site needs specific non-player-state reason and hashed evidence')
   continue
  if kind not in REQUIRED:errors.append(name+': unknown domain kind');continue
  cases=row.get('cases',{})
  for case in REQUIRED[kind]:
   c=cases.get(case,{})
   if c.get('status')!='pass' or not evidence(c.get('evidence')) or len(str(c.get('observed','')).strip())<20:errors.append(name+': missing/untested/evidence-invalid '+case)
  targets=row.get('production_targets',[])
  target_files={sites[k]['file'] for k in owned if k in sites}
  if not targets or not all(t in files for t in targets) or not target_files.issubset(set(targets)):errors.append(name+': regression target list omits owned production files')
  if kind=='reward' and not all(any(t.startswith(layer+'/') for t in targets) for layer in ['native','web']):errors.append(name+': rewards need actual Native and Web targets, not a copied ledger fixture')
 return errors

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source',type=Path,required=True);ap.add_argument('--native',type=Path,required=True);ap.add_argument('--web',type=Path,required=True);ap.add_argument('--coverage',type=Path,required=True);ap.add_argument('--init',action='store_true');ap.add_argument('--out',type=Path)
 a=ap.parse_args();roots={'source':a.source.resolve(),'native':a.native.resolve(),'web':a.web.resolve()}
 if any(not p.is_dir() for p in roots.values()):ap.error('all three artifact roots must exist')
 if a.init:
  if a.coverage.exists():ap.error('existing coverage is preserved; reconcile changed sites explicitly')
  files,sites=inventory(roots);a.coverage.parent.mkdir(parents=True,exist_ok=True)
  a.coverage.write_text(json.dumps({'schema':'runtime_coverage.v1','artifacts':files,'sites':{k:{'discovered':v,'domain':''} for k,v in sites.items()},'domains':{}},indent=2)+'\n');return 0
 try:doc=json.loads(a.coverage.read_text());errors=verify(doc,roots,a.coverage.parent)
 except (OSError,ValueError,TypeError,AttributeError) as e:errors=['invalid/missing coverage: '+str(e)]
 report={'tool':'audit_runtime_coverage','passed':not errors,'errors':errors,'boundary':'hashes/ownership/evidence completeness only; does not prove observation truth or real platform acceptance'}
 if a.out:a.out.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report));return bool(errors)
if __name__=='__main__':sys.exit(main())
