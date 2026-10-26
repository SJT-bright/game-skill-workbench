"""Append-only game production accounting; no daemon, chat export, quota inference or billing claims."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
import subprocess
from pathlib import Path
import uuid

FIELDS = ('input_tokens', 'cached_input_tokens', 'output_tokens', 'reasoning_output_tokens')

def stamp(value=None):
    d = datetime.fromisoformat(value.replace('Z', '+00:00')) if value else datetime.now(timezone.utc)
    if d.tzinfo is None: raise ValueError('timestamp requires timezone')
    return d.astimezone(timezone.utc).isoformat()

def seconds(value): return datetime.fromisoformat(value).timestamp()

def union(intervals):
    total = 0; end = None
    for a, b in sorted(intervals):
        if b < a: raise ValueError('negative interval')
        total += max(0, b - max(a, end if end is not None else a)); end = max(b, end if end is not None else b)
    return total

@contextmanager
def lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path)+'.lock', os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try: yield
    finally: os.close(fd); Path(str(path)+'.lock').unlink()

def read(path):
    if not path.exists(): return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

def append(path, rows):
    with path.open('a', encoding='utf8') as f:
        for row in rows: f.write(json.dumps(row, ensure_ascii=False)+'\n')
        f.flush(); os.fsync(f.fileno())

def usage_record(payload, at, owner, source):
    rid = payload.get('response_id'); u = payload.get('usage')
    if not rid or not isinstance(u, dict): raise ValueError('per-response usage needs response_id and usage')
    if payload.get('thread_id', owner) != owner: return None
    if not all(type(u.get(k, 0)) is int and u.get(k, 0) >= 0 for k in FIELDS): raise ValueError('invalid token values')
    if 'input_tokens' not in u or 'output_tokens' not in u: raise ValueError('missing input/output')
    if u.get('cached_input_tokens', 0) > u['input_tokens'] or u.get('reasoning_output_tokens', 0) > u['output_tokens']: raise ValueError('subset tokens invalid')
    total = u['input_tokens'] + u['output_tokens']
    if u.get('total_tokens', total) != total: raise ValueError('invalid total_tokens')
    return dict(type='usage', id=rid, at=stamp(at), owner=owner, model=payload.get('model', 'unknown'), source=source,
                counts={**{k:u.get(k, 0) for k in FIELDS}, 'total_tokens':total},
                subsets_available={k:k in u for k in ('cached_input_tokens','reasoning_output_tokens')})

def import_usage(path, events, owner):
    """Import only explicit owner events; legacy cumulative counters remain unknown, never charged."""
    previous = [e for e in events if e['type']=='scan' and e['source']==str(path)]
    offset = previous[-1]['offset'] if previous else 0
    with path.open('rb') as stream: prefix = hashlib.sha256(stream.read(min(offset,4096))).hexdigest()
    if previous and (path.stat().st_size < offset or prefix != previous[-1]['prefix_sha256']): raise ValueError('log replaced/truncated; inspect and rebind')
    with path.open('rb') as f:
        first = json.loads(f.readline()); meta = first.get('payload', {})
        if first.get('type')!='session_meta' or meta.get('id')!=owner: raise ValueError('session owner mismatch')
        created = seconds(stamp(meta['timestamp']))
        project=next((e for e in events if e['type']=='project'),None)
        if project: created=max(created,seconds(project['at']))
        bound=[]; opened=None
        for event in events:
            if event.get('owner')!=owner: continue
            if event['type']=='bind': opened=seconds(event['at'])
            elif event['type']=='unbind' and opened is not None:
                bound.append((opened,seconds(event['at'])));opened=None
        closed=next((seconds(e['at']) for e in events if e['type']=='close'),float('inf'))
        if opened is not None: bound.append((opened,closed))
        f.seek(offset); pending=[]; legacy=0
        known={e['id']:e for e in events if e['type']=='usage'}
        while True:
            pos=f.tell(); line=f.readline()
            if not line: break
            if not line.endswith(b'\n'): f.seek(pos); break
            x=json.loads(line); p=x.get('payload', {})
            if x.get('type')!='event_msg' or not x.get('timestamp'): continue
            observed=seconds(stamp(x['timestamp']))
            if observed < created or observed > closed: continue
            if project and not any(lo<=observed<hi for lo,hi in bound): continue
            if p.get('type')=='token_count': legacy+=1; continue
            if p.get('type')!='token_usage_record': continue
            row=usage_record(p,x['timestamp'],owner,{'path':str(path),'offset':pos})
            if row is None: continue
            if row['id'] in known:
                if any(row[k]!=known[row['id']][k] for k in ('owner','model','counts','subsets_available')): raise ValueError('conflicting response_id')
                continue
            known[row['id']]=row; pending.append(row)
        offset=f.tell()
    with path.open('rb') as stream: prefix=hashlib.sha256(stream.read(min(offset,4096))).hexdigest()
    pending.append(dict(type='scan',at=stamp(),source=str(path),owner=owner,offset=offset,prefix_sha256=prefix,legacy_events_ignored=legacy))
    return pending

def summary(events, until=None):
    project=next(e for e in events if e['type']=='project')
    end=until or next((e['at'] for e in reversed(events) if e['type']=='close'),stamp())
    starts={e['id']:e for e in events if e['type']=='start'}; stops={e['id']:e for e in events if e['type']=='stop'}
    phases={}; intervals=[]; tasks=[]
    for ident,s in starts.items():
        if ident not in stops: continue
        t=stops[ident]; a,b=seconds(s['at']),seconds(t['at'])
        if a < seconds(project['at']) or b > seconds(end): raise ValueError('task outside project window')
        intervals.append((a,b))
        phase=phases.setdefault(s['phase'],{'intervals':[], 'kinds':{},'tasks':0,'failed_tasks':0,'tokens':0})
        phase['intervals'].append((a,b)); phase['kinds'].setdefault(s['kind'],[]).append((a,b)); phase['tasks']+=1
        phase['failed_tasks']+=int(t['result']=='fail')
        tasks.append(dict(id=ident,phase=s['phase'],task=s['task'],kind=s['kind'],owner=s['owner'],start=s['at'],end=t['at'],seconds=b-a,result=t['result'],tested=t['tested'],evidence=t['evidence']))
    totals={k:0 for k in (*FIELDS,'total_tokens')}; unallocated=0; calls=0
    subset_known={k:True for k in ('cached_input_tokens','reasoning_output_tokens')}
    for e in events:
        if e['type']!='usage': continue
        calls+=1
        for k in totals: totals[k]+=e['counts'][k]
        for k in subset_known: subset_known[k] &= e['subsets_available'][k]
        # Completion-time attribution is explicit, never presented as exact phase billing.
        match={s['phase'] for ident,s in starts.items() if s['owner']==e['owner'] and ident in stops and seconds(s['at'])<=seconds(e['at'])<seconds(stops[ident]['at']) and s['kind']=='work'}
        if len(match)==1: phases[next(iter(match))]['tokens']+=e['counts']['total_tokens']
        else: unallocated+=e['counts']['total_tokens']
    for p in phases.values():
        p['recorded_elapsed_seconds']=union(p.pop('intervals')); p['seconds_by_kind']={k:union(v) for k,v in p['kinds'].items()}; del p['kinds']
    for k,known in subset_known.items():
        if not known or not calls: totals[k]=None
    totals['uncached_input_tokens']=None if totals['cached_input_tokens'] is None else totals['input_tokens']-totals['cached_input_tokens']
    if not calls:
        for phase in phases.values(): phase['tokens']=None
    wall=seconds(end)-seconds(project['at'])
    if wall<0: raise ValueError('close before project start')
    return dict(schema='game-production-summary.v1',project=project['name'],start=project['at'],end=end,closed=any(e['type']=='close' for e in events),
        historical_start_unknown=project.get('historical_start_unknown',False),wall_seconds=wall,recorded_interval_union_seconds=union(intervals),unrecorded_wall_seconds=max(0,wall-union(intervals)),
        time_note='Interval unions include work/tool/wait; not pure model inference or human labor. Kind/phase unions may overlap: never add to obtain project duration.',
        phases=phases,tasks=tasks,notes=[e for e in events if e['type']=='note'],open_tasks=[i for i in starts if i not in stops],usage=dict(status='partial_observed' if calls else 'unknown_no_per_response_records',calls=calls,known=totals,unallocated_tokens=unallocated,attribution='completion_timestamp; boundary-crossing calls may be approximate; ambiguous/uncovered calls unallocated'),
        quota=dict(status='account_snapshots_only' if any(e['type']=='quota' for e in events) else 'unknown_no_stage_meter',project_consumption=None,snapshots=[e for e in events if e['type']=='quota']),money=dict(status='unknown_no_billing_or_price_table',value=None),
        limits=['Only explicitly bound sessions and imported records; missing sessions/providers unknown.', 'Cached input is within input; reasoning output is within output.', 'Legacy cumulative counters excluded; no inherited-token or quota conversion.', 'Latest live response usage may arrive after this snapshot; reimport after next turn.'])

def price_usage(events, pricing):
    if not isinstance(pricing.get('models'),dict) or not pricing.get('as_of') or not pricing.get('source') or not pricing.get('currency'): raise ValueError('pricing needs models/as_of/source/currency')
    amount=0; missing=0
    for e in events:
        if e['type']!='usage': continue
        rates=pricing['models'].get(e['model']); u=e['counts']
        if rates is None or not e['subsets_available']['cached_input_tokens']: missing+=1; continue
        keys=('input_per_million','cached_input_per_million','output_per_million')
        if any(type(rates.get(k)) not in (int,float) or rates[k]<0 for k in keys): raise ValueError('invalid pricing')
        amount+=((u['input_tokens']-u['cached_input_tokens'])*rates[keys[0]]+u['cached_input_tokens']*rates[keys[1]]+u['output_tokens']*rates[keys[2]])/1000000
    return dict(status='unknown_no_per_response_records' if not any(e['type']=='usage' for e in events) else 'partial_estimate' if missing else 'price_table_estimate',estimated_amount=amount if any(e['type']=='usage' for e in events) else None,currency=pricing['currency'],as_of=pricing['as_of'],source=pricing['source'],unpriced_calls=missing,actual_billed=None,note='Price-table estimate only; subscription quota and actual bills are separate.')

def report_text(r):
    lines=[f"# {r['project']} 制作统计",'',f"状态：{'项目已完结' if r['closed'] else '进行中快照'}",f"{'历史开工未知；本次开始记录' if r['historical_start_unknown'] else '开工'}：{r['start']}；截止：{r['end']}",f"总历时：{r['wall_seconds']/3600:.2f}小时；已记录区间并集：{r['recorded_interval_union_seconds']/3600:.2f}小时；未记录：{r['unrecorded_wall_seconds']/3600:.2f}小时。",r['time_note'],'','| 阶段 | 记录历时(分钟) | 工作/工具/等待(分钟，各自并集) | 已归属token | 任务/失败 |','|---|---:|---|---:|---|']
    for phase,p in r['phases'].items(): lines.append(f"| {phase} | {p['recorded_elapsed_seconds']/60:.1f} | "+' / '.join(f"{k}:{v/60:.1f}" for k,v in p['seconds_by_kind'].items())+f" | {p['tokens']} | {p['tasks']}/{p['failed_tasks']} |")
    lines+=['',f"用量覆盖：{r['usage']['status']}；实际读到的调用：{r['usage']['calls']}。",'已观测token：'+json.dumps(r['usage']['known'],ensure_ascii=False),f"未分阶段token：{r['usage']['unallocated_tokens']}。阶段按调用完成时间归属，跨边界可能近似。",'额度百分比：未知；货币成本：'+json.dumps(r['money'],ensure_ascii=False)+'。不把token换算为订阅额度。','','## 工作与测试明细','']
    for t in r['tasks']: lines.append(f"- {t['phase']} / {t['task']}：{t['seconds']/60:.1f}分钟，{t['result']}；测试：{'; '.join(t['tested']) or '未登记'}；证据："+', '.join(e['path'] for e in t['evidence']))
    lines+=['','## 优化观察','']
    for phase,p in sorted(r['phases'].items(),key=lambda kv:kv[1]['recorded_elapsed_seconds'],reverse=True)[:3]: lines.append(f"- {phase}：记录历时{p['recorded_elapsed_seconds']/60:.1f}分钟，已归属{p['tokens']} token，失败任务{p['failed_tasks']}。先结合返工原因和重复测试证据分析，不仅凭耗时判浪费。")
    lines += ['', *[f"- {n['phase']} / {n['tag']}：{n['text']}" for n in r['notes']]]
    lines+=['','缺失数据不得视为0；结案汇总须另写具体返工原因、可复用结果和有证据的改进建议。',*r['limits']]
    return '\n'.join(lines)+'\n'

def run_command(root, args):
    path=root/'docs/production/accounting.jsonl'; ident=str(uuid.uuid4())
    command=args.command[1:] if args.command and args.command[0]=='--' else args.command
    if not command: raise ValueError('run needs a command after --')
    with lock(path):
        events=read(path)
        if not events or any(e['type']=='close' for e in events): raise ValueError('initialize an open project first')
        if next((e['type'] for e in reversed(events) if e['type'] in ('bind','unbind') and e['owner']==args.owner),None)!='bind': raise ValueError('bind owner first')
        append(path,[dict(type='start',id=ident,at=stamp(),phase=args.phase,task=args.task,kind='tool',owner=args.owner)])
    code=1
    try: code=subprocess.run(command,cwd=root).returncode
    finally:
        with lock(path): append(path,[dict(type='stop',id=ident,at=stamp(),result='pass' if code==0 else 'fail',tested=args.tested,evidence=[],exit_code=code)])
    print(json.dumps(dict(task_id=ident,exit_code=code)))
    return code

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',type=Path,required=True)
    sub=p.add_subparsers(dest='cmd',required=True)
    i=sub.add_parser('init');i.add_argument('--name',required=True);i.add_argument('--at');i.add_argument('--historical-start-unknown',action='store_true')
    b=sub.add_parser('bind');b.add_argument('--owner',required=True);b.add_argument('--at')
    ub=sub.add_parser('unbind');ub.add_argument('--owner',required=True);ub.add_argument('--at')
    s=sub.add_parser('start');s.add_argument('--id',default=None);s.add_argument('--phase',required=True);s.add_argument('--task',required=True);s.add_argument('--kind',choices=['work','tool','wait'],default='work');s.add_argument('--owner',required=True);s.add_argument('--at')
    t=sub.add_parser('stop');t.add_argument('--id',required=True);t.add_argument('--result',choices=['pass','fail','done','approved','blocked','cancelled'],required=True);t.add_argument('--tested',action='append',default=[]);t.add_argument('--evidence',action='append',type=Path,default=[]);t.add_argument('--at')
    u=sub.add_parser('import-usage');u.add_argument('--file',type=Path,required=True);u.add_argument('--owner',required=True)
    run=sub.add_parser('run');run.add_argument('--phase',required=True);run.add_argument('--task',required=True);run.add_argument('--owner',required=True);run.add_argument('--tested',action='append',required=True);run.add_argument('command',nargs=argparse.REMAINDER)
    note=sub.add_parser('note');note.add_argument('--phase',required=True);note.add_argument('--tag',choices=['rework','decision','optimization','coverage'],required=True);note.add_argument('--text',required=True)
    q=sub.add_parser('quota');q.add_argument('--file',type=Path,required=True)
    rr=sub.add_parser('report');rr.add_argument('--pricing',type=Path);c=sub.add_parser('close');c.add_argument('--pricing',type=Path);c.add_argument('--at');c.add_argument('--registry',type=Path)
    a=p.parse_args();root=a.project.resolve();path=root/'docs/production/accounting.jsonl'
    if a.cmd=='run': return run_command(root,a)
    with lock(path):
        events=read(path);rows=[]
        if a.cmd=='init':
            if events: raise ValueError('project already initialized; reuse ledger')
            rows=[dict(type='project',name=a.name,at=stamp(a.at),schema='game-production-ledger.v1',historical_start_unknown=a.historical_start_unknown)]
        elif not events: raise ValueError('init project first')
        elif a.cmd in ('bind','unbind'):
            history=[e for e in events if e['type'] in ('bind','unbind') and e['owner']==a.owner]
            active=bool(history and history[-1]['type']=='bind')
            if a.cmd=='unbind' and any(e['type']=='start' and e['owner']==a.owner and not any(t['type']=='stop' and t['id']==e['id'] for t in events) for e in events): raise ValueError('stop owner tasks before unbinding')
            if active != (a.cmd=='bind'): rows=[dict(type=a.cmd,owner=a.owner,at=stamp(a.at))]
        elif a.cmd=='start':
            if any(e['type']=='close' for e in events): raise ValueError('closed project: start a new production run, preserve prior ledger')
            if next((e['type'] for e in reversed(events) if e['type'] in ('bind','unbind') and e['owner']==a.owner),None)!='bind': raise ValueError('bind owner first')
            ident=a.id or str(uuid.uuid4()); row=dict(type='start',id=ident,at=stamp(a.at),phase=a.phase,task=a.task,kind=a.kind,owner=a.owner)
            old=next((e for e in events if e['type']=='start' and e['id']==ident),None)
            if old: raise ValueError('task id already used')
            rows=[row]
        elif a.cmd=='stop':
            start=next(e for e in events if e['type']=='start' and e['id']==a.id)
            if any(e['type']=='stop' and e['id']==a.id for e in events): raise ValueError('task already stopped')
            at=stamp(a.at)
            if seconds(at)<seconds(start['at']): raise ValueError('stop before start')
            evidence=[]
            for f in a.evidence:
                f=(root/f).resolve()
                if root not in f.parents: raise ValueError('evidence must be inside project')
                evidence.append(dict(path=str(f.relative_to(root)),sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
            rows=[dict(type='stop',id=a.id,at=at,result=a.result,tested=a.tested,evidence=evidence)]
        elif a.cmd=='import-usage':
            if next((e['type'] for e in reversed(events) if e['type'] in ('bind','unbind') and e['owner']==a.owner),None)!='bind': raise ValueError('bind owner first')
            rows=import_usage(a.file.resolve(),events,a.owner)
        elif a.cmd=='note':
            rows=[dict(type='note',at=stamp(),phase=a.phase,tag=a.tag,text=a.text)]
        elif a.cmd=='quota':
            data=json.loads(a.file.read_text()); windows=[]
            for w in data['windows']:
                value=w.get('used_percent')
                if type(value) not in (int,float) or not 0<=value<=100: raise ValueError('invalid quota percent')
                windows.append(dict(id=str(w['id']),used_percent=value,resets_at=w['resets_at']))
            rows=[dict(type='quota',at=stamp(data.get('at')),scope='account_shared_not_project',windows=windows)]
        elif a.cmd=='close':
            if summary(events)['open_tasks']: raise ValueError('close known intervals first; do not count idle overnight as work')
            if not any(e['type']=='close' for e in events): rows=[dict(type='close',at=stamp(a.at))]
        candidate=events+rows
        if a.cmd in ('report','close'):
            result=summary(candidate)
            if a.pricing: result['money']=price_usage(candidate,json.loads(a.pricing.read_text()))
        append(path,rows)
        if a.cmd in ('report','close'):
            (path.parent/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
            (path.parent/'summary.md').write_text(report_text(result))
        if a.cmd=='close' and a.registry:
            registry=a.registry.resolve()
            with lock(registry):
                existing=read(registry);entry=dict(project=str(root),summary=str(path.parent/'summary.json'),closed=result['end'],summary_sha256=hashlib.sha256((path.parent/'summary.json').read_bytes()).hexdigest())
                if entry not in existing: append(registry,[entry])
    print(json.dumps({'status':'ok','command':a.cmd,'ledger':str(path),'events_added':len(rows),'task_id':rows[0].get('id') if rows else None},ensure_ascii=False))

if __name__=='__main__':
    try: raise SystemExit(main())
    except (ValueError,KeyError,StopIteration,OSError,json.JSONDecodeError) as e: raise SystemExit('accounting refused: '+str(e))
