#!/usr/bin/env python3
"""Early modal-input risk inventory. Never certifies interaction or device acceptance."""
import argparse, hashlib, json, shutil, subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent

def scan(project):
    candidates=[]
    for file in sorted((Path(project)/'assets').rglob('*')):
        if file.suffix not in {'.js','.ts','.mjs','.cjs'} or set(file.parts)&{'node_modules','.git'}:continue
        source=file.read_text(encoding='utf-8-sig',errors='replace')
        if 'getChildByName' in source and any(word in source.lower() for word in ['mask','shade','blackbg','backdrop','blocker','overlay']):
            candidates.append((file,source))
    if not candidates:return {'source_risks':[],'unresolved':[],'candidate_files':0}
    node=shutil.which('node')
    if not node:return {'source_risks':[],'unresolved':[{'path':str(f),'reason':'Node.js required for lexical inspection'} for f,_ in candidates],'candidate_files':len(candidates)}
    run=subprocess.run([node,str(HERE/'scan_modal_ownership.cjs')],input=json.dumps({'sources':[s for _,s in candidates]}),text=True,capture_output=True,timeout=30)
    if run.returncode:raise ValueError('modal source inventory failed: '+run.stderr[-300:])
    rows=json.loads(run.stdout)
    if len(rows)!=len(candidates):raise ValueError('modal source inventory lost candidates')
    risks=[];unresolved=[]
    for (file,_),row in zip(candidates,rows):
        ref={'path':file.relative_to(project).as_posix(),'sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
        risks.extend(dict(item,**ref) for item in row['risks'])
        if row['status']!='scanned':unresolved.append(dict(ref,reason=row.get('reason','unresolved syntax')))
    return {'source_risks':risks,'unresolved':unresolved,'candidate_files':len(candidates)}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',required=True,type=Path);parser.add_argument('--out',required=True,type=Path)
    a=parser.parse_args();project=a.project.resolve();result=scan(project)
    result.update(tool='audit_modal_ownership',stage='source_only',passed=False,runtime_required=True,
                  boundary='Lexical risk inventory only; no risk found does not prove safe modal ownership. Validate actual open/close input in modal_lifecycle. No phone claim.')
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False));return int(bool(result['source_risks'] or result['unresolved']))

if __name__=='__main__':raise SystemExit(main())
