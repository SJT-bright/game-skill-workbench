#!/usr/bin/env python3
"""Named, durable, input-bound production checks for images, text, audio, gameplay and levels.

Each node invokes a real checker and reads its real verdict file. Completing work or
writing a status note cannot create a passed check. No full-run or force-pass option.
"""
import argparse
import json
from pathlib import Path
import subprocess
import shutil
import sys
import uuid
import check_ledger as C

SCHEMA='check-workflow.v1'
PHASES={1:'盘点与基线',2:'制作与首次验证',3:'Native 试玩前覆盖核对',4:'点对点返工',5:'补缺与写包核对'}

def read(project,file=None):
    file=Path(file or project/'docs/checks/workflow.json')
    doc=json.loads(file.read_text())
    if doc.get('schema')!=SCHEMA or doc.get('route') not in ('source','handoff'):
        raise ValueError('工作流须声明 check-workflow.v1 和 source/handoff 两条入口之一')
    nodes=doc.get('nodes',[]);ids=[n['id'] for n in nodes]
    if not ids or len(ids)!=len(set(ids)):raise ValueError('节点不能为空或重名')
    for n in nodes:
        if n.get('domain') not in C.DOMAINS or n.get('phase') not in PHASES or not n.get('label'):
            raise ValueError(n['id']+'：缺少类别、阶段或节点名称')
        if not isinstance(n.get('command'),list) or not n['command'] or not n.get('tool_files'):
            raise ValueError(n['id']+'：必须给出真实检查器命令和规则文件')
        if not isinstance(n.get('inputs'),dict) or not n['inputs'] or not n.get('basis'):
            raise ValueError(n['id']+'：必须登记完整依赖及引用依据')
        if not isinstance(n.get('verdict'),dict) or not n['verdict'].get('file') or n['verdict'].get('equals') is not True:
            raise ValueError(n['id']+'：必须读取实际检查报告中的 true 判定')
        if set(n.get('after',[]))-set(ids):raise ValueError(n['id']+'：前置节点不存在')
    visiting=set();done=set();by={n['id']:n for n in nodes}
    def visit(cid):
        if cid in visiting:raise ValueError('节点依赖成环：'+cid)
        if cid in done:return
        visiting.add(cid)
        for d in by[cid].get('after',[]):visit(d)
        visiting.remove(cid);done.add(cid)
    for cid in ids:visit(cid)
    return doc

def expand(value,project):
    return str(value).replace('${PROJECT}',str(project)).replace('${SKILLS}',str(Path(__file__).resolve().parents[2])).replace('${PYTHON}',sys.executable)

def roots_of(doc,project):
    roots={}
    for name,path in doc.get('roots',{}).items():
        p=Path(expand(path,project));p=p if p.is_absolute() else project/p
        roots[name]=C.manifest(p)
    if not roots:raise ValueError('工作流缺少输入根目录')
    return roots

def register(doc,project):
    file=project/'docs/checks/check-inputs.json'
    data=json.loads(file.read_text()) if file.is_file() else {'schema':C.SCOPE_SCHEMA,'checks':{}}
    if data.get('schema')!=C.SCOPE_SCHEMA:raise ValueError('既有依赖登记格式不兼容')
    for n in doc['nodes']:data['checks'][n['id']]={'basis':n['basis'],'inputs':n['inputs']}
    file.parent.mkdir(parents=True,exist_ok=True)
    content=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
    if not file.exists() or file.read_text()!=content:file.write_text(content)

def prepare(ledger,doc,project):
    register(doc,project);roots=roots_of(doc,project);plans=[]
    for n in doc['nodes']:
        command=[expand(a,project) for a in n['command']]
        outputs=[expand(a,project) for a in n.get('outputs',[])]+[expand(n['verdict']['file'],project)]
        logical=[next(('<output-%d>'%i for i,p in enumerate(outputs) if p==arg),arg) for arg in command]
        logical=[a.replace(str(project),'${PROJECT}').replace(str(Path(__file__).resolve().parents[2]),'${SKILLS}') for a in logical]
        files=[Path(expand(a,project)) for a in n['tool_files']]
        if any(not p.is_file() for p in files):raise ValueError(n['id']+'：真实检查器文件不存在')
        files.extend([Path(__file__),Path(C.__file__)])
        plans.append(ledger.prepare(n['id'],roots,{'command':logical,'conditions':n.get('conditions',{}),
                     'required_output_slots':len(n.get('outputs',[]))+1,
                     'verdict':{k:v for k,v in n['verdict'].items() if k!='file'}},C.tool_fingerprint(files),
                     label=n['label'],domain=n['domain']))
    return plans

def run_node(ledger,doc,project,cid):
    plans=prepare(ledger,doc,project);by={p['check_id']:p for p in plans};node=next((n for n in doc['nodes'] if n['id']==cid),None)
    if not node:raise ValueError('没有这个节点：'+cid)
    # Prior nodes supply evidence; they are never re-executed as an automatic prerequisite.
    gap=[d for d in node.get('after',[]) if by[d]['action']!='reuse']
    if gap:raise C.NeedsScope('前置证据需要处理：'+','.join(gap)+'；不会自动重跑它们')
    command=[expand(a,project) for a in node['command']]
    verdict=Path(expand(node['verdict']['file'],project))
    if not verdict.is_absolute():verdict=project/verdict
    destinations=[verdict,*[Path(expand(p,project)) for p in node.get('outputs',[])]]
    destinations=list(dict.fromkeys(p if p.is_absolute() else project/p for p in destinations))
    def execute():
        # Preserve old artifacts outside the checker's destinations. Touching an
        # old report, or returning 0 without producing a new one, cannot pass.
        existing=[p for p in destinations if p.exists() or p.is_symlink()]
        for p in existing:
            if p.is_symlink() or not p.is_file():
                raise C.NeedsScope('检查输出必须是独立文件，先定位该路径：'+str(p))
        backup=None
        if existing:
            backup=ledger.home/'superseded-outputs'/uuid.uuid4().hex
            backup.mkdir(parents=True,exist_ok=False)
            saved=[]
            for index,p in enumerate(existing):
                target=backup/(str(index)+'-'+p.name)
                digest=C.sha(p.read_bytes())
                shutil.move(str(p),str(target))
                saved.append({'original':str(p),'backup':str(target),'sha256':digest})
            (backup/'manifest.json').write_text(json.dumps(saved,ensure_ascii=False,indent=2)+'\n')
        proc=subprocess.run(command,cwd=expand(node.get('cwd','${PROJECT}'),project),capture_output=True,text=True,
                            timeout=node.get('timeout_seconds',1800))
        fresh=verdict.is_file() and not verdict.is_symlink()
        missing=[str(p) for p in destinations if not p.is_file() or p.is_symlink()]
        report={};parse_error=None
        if fresh:
            try:report=json.loads(verdict.read_text())
            except (ValueError,OSError) as exc:parse_error=str(exc)
        ok=(proc.returncode==0 and fresh and not missing and not parse_error
            and C.pointer(report,node['verdict'].get('pointer','/passed')) is True)
        return {'passed':ok,'returncode':proc.returncode,'fresh_verdict':fresh,'report':str(verdict) if fresh else None,
                'stdout':proc.stdout,'stderr':proc.stderr,'missing_outputs':missing,'report_error':parse_error,
                'previous_outputs_backup':str(backup) if backup else None,
                'outputs':[str(p.resolve()) if p.is_file() else None for p in destinations]}
    result,proof=ledger.execute(by[cid],execute,lambda r:r['passed'],
        verify_inputs=lambda:C.select_inputs(roots_of(doc,project),by[cid]['scope']))
    if proof['reused']:
        for target,source in zip(destinations,result.get('outputs',[])):
            if not source:continue
            target.parent.mkdir(parents=True,exist_ok=True)
            if not target.is_file() or C.sha(target.read_bytes())!=C.sha(Path(source).read_bytes()):
                shutil.copy2(source,target)
    return result,proof

def overview(ledger,doc,project):
    plans=prepare(ledger,doc,project);state=ledger.status();by={n['id']:n for n in doc['nodes']}
    return {'schema':SCHEMA,'project':str(project),'route':doc['route'],
        'nodes':[dict(id=p['check_id'],label=p['label'],domain=p['domain'],phase=by[p['check_id']]['phase'],
            phase_name=PHASES[by[p['check_id']]['phase']],action=p['action'],reason=p['why'],
            original_at=(p['record'] or {}).get('executed_at'),seconds=(p['record'] or {}).get('seconds'),
            estimate_seconds=by[p['check_id']].get('estimate_seconds'),after=by[p['check_id']].get('after',[])) for p in plans],
        'events':state['events'],'executions':state['executions'],'reuses':state['reuses'],
        'next':[p['check_id'] for p in plans if p['action']!='reuse']}

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--project',type=Path,required=True)
    ap.add_argument('--workflow',type=Path);ap.add_argument('--out',type=Path)
    sub=ap.add_subparsers(dest='cmd',required=True);sub.add_parser('plan');sub.add_parser('status')
    run=sub.add_parser('run');run.add_argument('node')
    a=ap.parse_args();project=a.project.resolve();ledger=C.Ledger(project)
    try:
        doc=read(project,a.workflow)
        if a.cmd=='run':result,proof=run_node(ledger,doc,project,a.node);data={'node':a.node,'result':result,'execution':proof}
        else:data=overview(ledger,doc,project)
        content=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
        if a.out:a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(content)
        print(content)
        return 0 if a.cmd!='run' or data['result']['passed'] else 1
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        print('节点未执行：'+str(exc),file=sys.stderr);return 3
    finally:ledger.close()

if __name__=='__main__':raise SystemExit(main())
