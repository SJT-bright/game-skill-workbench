#!/usr/bin/env python3
"""Persistent, input-bound check records. A changed input needs a declared scope, never a full-run fallback.

The ledger schedules executions; it does not manufacture passes. Callers supply their
existing result validator. Stored evidence is copied and hashed before a result is reusable.
"""
import argparse
import ast
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import time
import uuid

SCHEMA = 'check-ledger.v1'
SCOPE_SCHEMA = 'check-inputs.v1'
DOMAINS = {'image':'图片', 'text':'文字/字幕', 'audio':'音效', 'gameplay':'玩法',
           'levels':'关卡', 'platform':'平台入口', 'startup':'启动', 'package':'写包', 'environment':'环境'}
IGNORED = {'.git', '.svn', '__pycache__', '.DS_Store'}


class NeedsScope(ValueError):
    """No execution is authorized until this precise dependency gap is resolved."""


class AlreadyRunning(NeedsScope):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sha(value):
    return hashlib.sha256(value if isinstance(value, bytes) else canonical(value).encode()).hexdigest()


def stamp():
    return time.strftime('%Y-%m-%dT%H:%M:%S%z')


def project_of(package=None, adapter=None):
    if os.environ.get('ENGLISH_CHECK_PROJECT'):
        return Path(os.environ['ENGLISH_CHECK_PROJECT']).resolve()
    if adapter:
        p=Path(adapter).resolve().parent
        for root in [p, *p.parents]:
            if (root/'assets').is_dir() and ((root/'project.json').exists() or (root/'package.json').exists()):
                return root
        if p.name == 'qa':return p.parent
        if p.name == 'checks' and p.parent.name == 'docs':return p.parent.parent
    p=Path(package or '.').resolve()
    for root in [p, *p.parents]:
        if (root/'assets').is_dir() and ((root/'project.json').is_file() or (root/'package.json').is_file()):
            return root
    return p


def manifest(root, *, project=False):
    """Contents, not timestamps. Project-generated reports are not source dependencies."""
    root=Path(root).resolve()
    if root.is_file():
        return {root.name:sha(root.read_bytes())}
    if not root.is_dir():
        return {'<missing>':sha(str(root))}
    out={}
    for p in sorted(root.rglob('*')):
        rel=p.relative_to(root)
        if set(rel.parts)&IGNORED or rel.parts[:3] == ('docs','checks','incremental') or (project and rel.parts[0] in ('docs','build','qa','.tiktok-kit','node_modules','temp','library')):
            continue
        if p.is_symlink():
            # Resolve bytes, but reject a directory link; no hidden recursive trees.
            if p.is_dir():
                raise NeedsScope('依赖目录含链接，先显式登记真实路径：'+str(p))
        if p.is_file():
            out[rel.as_posix()]=sha(p.read_bytes())
    return out


def tool_fingerprint(paths):
    """Explicit tool files plus local Python imports. Callers include non-Python resources."""
    todo=[Path(p).resolve() for p in paths]; seen=set(); rows=[]
    while todo:
        p=todo.pop()
        if p in seen: continue
        seen.add(p)
        if p.is_dir():
            todo.extend(x for x in p.rglob('*') if x.is_file() and not set(x.parts)&IGNORED and x.suffix!='.pyc')
            continue
        if not p.is_file():
            rows.append((p.name,'missing')); continue
        raw=p.read_bytes()
        identity = sha(raw)
        if p == Path(__file__).resolve():
            try:
                compatibility = json.loads(p.with_name('check-ledger-rule-compat.json').read_text())
                if (compatibility.get('schema') == 'check-ledger-rule-compat.v1'
                        and compatibility.get('current_sha256') == identity
                        and compatibility.get('scope') == 'evidence-recovery-scheduling-only'):
                    identity = compatibility['prior_sha256']
            except (OSError, ValueError, KeyError, TypeError):
                pass
        rows.append((p.name,identity))
        if p.suffix=='.py':
            try:
                tree=ast.parse(raw)
                for node in ast.walk(tree):
                    names=([a.name for a in node.names] if isinstance(node,ast.Import)
                           else [node.module] if isinstance(node,ast.ImportFrom) and node.module else [])
                    for name in names:
                        target=p.parent/(name.replace('.','/')+'.py')
                        if target.is_file():todo.append(target)
            except (SyntaxError,UnicodeError):
                raise NeedsScope('检查器无法解析，不能使用旧记录：'+str(p))
    return sha(sorted(rows))


def pointer(value, path):
    if path=='': return value
    if not isinstance(path,str) or not path.startswith('/'):
        raise NeedsScope('JSON 依赖必须使用 JSON Pointer：'+repr(path))
    cur=value
    try:
        for key in path[1:].split('/'):
            key=key.replace('~1','/').replace('~0','~')
            cur=cur[int(key)] if isinstance(cur,list) else cur[key]
    except (KeyError,ValueError,TypeError,IndexError):
        return {'missing_json_pointer':path}
    return cur


def scope_for(project, check_id):
    file=Path(project)/'docs/checks/check-inputs.json'
    if not file.is_file():return None
    doc=json.loads(file.read_text())
    if doc.get('schema')!=SCOPE_SCHEMA or not isinstance(doc.get('checks'),dict):
        raise NeedsScope('检查范围文件格式不正确：'+str(file))
    row=doc['checks'].get(check_id)
    if row is None:return None
    if not isinstance(row,dict) or not isinstance(row.get('inputs'),dict) or not row['inputs']:
        raise NeedsScope(check_id+'：缺少实际输入依赖，不能用空范围豁免检查')
    if not row.get('basis'):
        raise NeedsScope(check_id+'：范围须说明源码引用、资源使用者或既有运行证据的依据')
    return row


def select_inputs(roots, scope):
    """Full unchanged inputs work immediately. Pruning requires a persisted dependency declaration.

    roots maps a logical name to a manifest {relative_path: sha}; declarations can use
    path globs. JSON pointers are supplied as virtual manifest entries by the caller.
    """
    if scope is None:return roots
    result={}
    for name, patterns in scope['inputs'].items():
        if name not in roots or not isinstance(patterns,list) or not patterns or not all(isinstance(s,str) and s for s in patterns):
            raise NeedsScope('无效依赖选择器：'+name)
        values=roots[name]
        result[name]={k:v for k,v in values.items() if any(fnmatch.fnmatchcase(k,p) for p in patterns)}
        # Preserve empty globs so later added dependencies invalidate this input.
        result[name]['<selectors>']=sha(patterns)
    return result


def unmapped_changes(project, old, new):
    """New/deleted inputs must have an owner; a glob's newly matching file also counts."""
    file=Path(project)/'docs/checks/check-inputs.json'
    doc=json.loads(file.read_text()) if file.is_file() else {}
    owners={}
    for row in doc.get('checks',{}).values():
        for root,patterns in row.get('inputs',{}).items():
            if isinstance(patterns,list):owners.setdefault(root,[]).extend(patterns)
    missing=[]
    for root in set(old)|set(new):
        a,b=old.get(root,{}),new.get(root,{})
        changed=[k for k in set(a)|set(b) if a.get(k)!=b.get(k)]
        for key in changed:
            # A JSON object's parent digest is an aggregate, not a second unowned leaf.
            if any(other.startswith(key.rstrip('/')+'/') for other in changed if other!=key):continue
            # Selecting a JSON object binds its aggregate hash, including every
            # child. A newly added leaf is owned by that exact object selector;
            # /states/0 does not own /states/01 or an adjacent /states/1.
            if not any(fnmatch.fnmatchcase(key,p) or
                       (p.startswith('/') and not any(c in p for c in '*?[')
                        and key.startswith(p.rstrip('/')+'/'))
                       for p in owners.get(root,[])):
                missing.append(root+':'+key)
    return sorted(missing)


def json_manifest(doc, prefix=''):
    result={prefix:sha(doc)}
    if isinstance(doc,dict):
        for k,v in doc.items():result.update(json_manifest(v,prefix+'/'+str(k).replace('~','~0').replace('/','~1')))
    elif isinstance(doc,list):
        for i,v in enumerate(doc):result.update(json_manifest(v,prefix+'/'+str(i)))
    return result


class Ledger:
    def __init__(self, project):
        self.project=Path(project).resolve()
        self.home=self.project/'docs/checks/incremental'
        self.home.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.home/'ledger.sqlite3',timeout=15)
        self.db.execute('CREATE TABLE IF NOT EXISTS records (key TEXT PRIMARY KEY, check_id TEXT, data TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS active (check_id TEXT PRIMARY KEY, key TEXT, pid INTEGER, token TEXT, started REAL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, data TEXT NOT NULL)')
        self.db.commit()
        self._file_checks={}

    def close(self):self.db.close()

    def event(self, check_id, state, **fields):
        row=dict(schema=SCHEMA,at=stamp(),epoch=time.time(),check_id=check_id,state=state,**fields)
        with self.db:self.db.execute('INSERT INTO events(data) VALUES(?)',(canonical(row),))
        return row

    def previous(self, check_id):
        rows=self.db.execute('SELECT data FROM records WHERE check_id=? ORDER BY rowid DESC',(check_id,))
        return [json.loads(r[0]) for r in rows]

    def _evidence_valid(self, row):
        for item in row.get('files',[]):
            p=Path(item['path'])
            if not p.is_file():return False
            stat=p.stat();signature=(str(p),stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns)
            digest=self._file_checks.get(signature)
            if digest is None:digest=sha(p.read_bytes());self._file_checks[signature]=digest
            if digest!=item['sha256']:return False
        return True

    def evidence_recheck(self, check_id, row):
        """An explicit per-node recovery record permits recollecting lost raw evidence."""
        file = self.project/'docs/checks/check-inputs.json'
        if not file.is_file():
            return None
        request = json.loads(file.read_text()).get('evidence_rechecks', {}).get(check_id)
        if not isinstance(request, dict) or not row or self._evidence_valid(row):
            return None
        searches = request.get('searched_locations')
        if (request.get('prior_key') != sha(row['binding'])
                or not isinstance(request.get('reason'), str) or not request['reason'].strip()
                or not isinstance(searches, list) or not searches
                or not all(isinstance(path, str) and Path(path).is_absolute() for path in searches)):
            raise NeedsScope(check_id+'：证据补采需要原记录key、恢复失败原因和已查找的绝对路径')
        return request

    def prepare(self, check_id, roots, conditions, tools, *, label=None, domain='gameplay'):
        if not check_id or domain not in DOMAINS:raise NeedsScope('检查节点必须有稳定 ID 和有效类别')
        scope=scope_for(self.project,check_id)
        inputs=select_inputs(roots,scope)
        value={'schema':SCHEMA,'check_id':check_id,'inputs':inputs,'conditions':conditions,'tool_sha256':tools,
               'scope_sha256':sha(scope) if scope else None}
        key=sha(value)
        found=self.db.execute('SELECT data FROM records WHERE key=?',(key,)).fetchone()
        cached=json.loads(found[0]) if found else None
        previous=self.previous(check_id)
        evidence_recheck = self.evidence_recheck(check_id, cached) if cached and cached.get('passed') else None
        if evidence_recheck:
            value['evidence_recheck'] = sha(evidence_recheck)
            key = sha(value)
            recovered = self.db.execute('SELECT data FROM records WHERE key=?', (key,)).fetchone()
            if recovered:
                cached = json.loads(recovered[0])
        unmapped=unmapped_changes(self.project,previous[0].get('roots',{}),roots) if scope and previous else []
        if unmapped:
            action='needs_scope';why='这些变化尚未关联到检查节点：'+', '.join(unmapped[:12])
        elif cached and cached.get('passed') and self._evidence_valid(cached):
            action='reuse';why='输入、相关规则、条件及原证据一致'
        elif cached and cached.get('passed') and evidence_recheck:
            action='run';why='原始证据无法恢复，仅重新采集此独立项：'+evidence_recheck['reason']
        elif cached and cached.get('passed'):
            action='evidence_missing';why='原通过证据丢失或变化；先恢复证据或定位该项，不自动重测整套'
        elif cached and not os.environ.get('CHECK_RETRY_REASON'):
            action='blocked_failed';why='该输入已失败；先修复输入，或登记真实环境恢复原因后只重试此项'
        elif previous and scope is None and any(r['binding']['inputs']!=inputs for r in previous):
            action='needs_scope';why='输入有变化，尚未登记受影响范围；填写 docs/checks/check-inputs.json 中此检查项的依赖'
        else:
            action='run';why='首次/新增检查项，或已声明的相关输入、规则、条件发生变化'
        # Adding a precise dependency declaration to a real prior execution is not a
        # new test. Retain the original execution identity, time and files.
        if not unmapped and scope and action == 'run':
            for row in previous:
                b=row['binding']
                if (row.get('passed') and b['conditions']==conditions and b['tool_sha256']==tools
                        and select_inputs(row.get('roots',{}),scope)==inputs and self._evidence_valid(row)):
                    cached=row;action='reuse';why='已通过的原执行覆盖此精确范围；只补依赖登记，不重测';break
        return dict(check_id=check_id,key=key,binding=value,action=action,why=why,record=cached,
                    label=label or check_id,domain=domain,roots=roots,scope=scope,
                    evidence_recheck=evidence_recheck)

    def _claim(self, plan):
        token=uuid.uuid4().hex
        self.db.execute('BEGIN IMMEDIATE')
        try:
            active=self.db.execute('SELECT key,pid,token,started FROM active WHERE check_id=?',(plan['check_id'],)).fetchone()
            if active:
                try:os.kill(active[1],0);alive=True
                except ProcessLookupError:alive=False
                except PermissionError:alive=True
                if alive:raise AlreadyRunning('节点正在执行，不能重复启动：%s PID=%s'%(plan['check_id'],active[1]))
                self.db.execute('DELETE FROM active WHERE check_id=?',(plan['check_id'],))
            # A different process may have completed after prepare().
            row=self.db.execute('SELECT data FROM records WHERE key=?',(plan['key'],)).fetchone()
            if row:
                row=json.loads(row[0])
                if row.get('passed') and self._evidence_valid(row):
                    self.db.commit();return None,row
            self.db.execute('INSERT INTO active VALUES(?,?,?,?,?)',(plan['check_id'],plan['key'],os.getpid(),token,time.time()))
            self.db.commit();return token,None
        except BaseException:
            self.db.rollback();raise

    def _freeze(self, value, folder, files):
        if isinstance(value,dict):return {k:self._freeze(v,folder,files) for k,v in value.items()}
        if isinstance(value,list):return [self._freeze(v,folder,files) for v in value]
        if isinstance(value,str) and len(value)<4096 and value.startswith('/'):
            p=Path(value)
            if p.is_file():
                digest=sha(p.read_bytes());target=folder/(digest+p.suffix)
                if not target.exists():shutil.copy2(p,target)
                files.append({'path':str(target),'sha256':digest})
                return str(target)
        return value

    def execute(self, plan, fn, passed, *, capture=None, verify_inputs=None):
        cid=plan['check_id'];start=time.monotonic()
        if plan['action']=='reuse':
            self.event(cid,'reused',source_key=sha(plan['record']['binding']),original_at=plan['record']['executed_at'],domain=plan['domain'],label=plan['label'])
            print('节点｜%s · %s：沿用，原检查 %s；未启动测试'%(DOMAINS[plan['domain']],plan['label'],plan['record']['executed_at']),file=sys.stderr)
            return plan['record']['result'],dict(reused=True,key=plan['key'],source_key=sha(plan['record']['binding']),original_at=plan['record']['executed_at'],seconds=0.0,original_seconds=plan['record']['seconds'])
        if plan['action']!='run':
            self.event(cid,plan['action'],reason=plan['why'],domain=plan['domain'],label=plan['label'])
            raise NeedsScope(cid+'：'+plan['why'])
        token,other=self._claim(plan)
        if other:
            plan.update(action='reuse',record=other);return self.execute(plan,fn,passed)
        print('节点｜%s · %s：开始；%s'%(DOMAINS[plan['domain']],plan['label'],plan['why']),file=sys.stderr)
        self.event(cid,'running',domain=plan['domain'],label=plan['label'],reason=plan['why'],key=plan['key'])
        result=None;ok=False;error=None
        try:
            result=fn()
            ok=passed(result) is True
            if verify_inputs and verify_inputs()!=plan['binding']['inputs']:
                ok=False;raise NeedsScope(cid+'：执行期间输入变化，不能给新字节沿用这次结果')
        except BaseException as exc:
            error=type(exc).__name__+': '+str(exc);raise
        finally:
            elapsed=round(time.monotonic()-start,6)
            try:
                folder=self.home/'evidence'/plan['key'];folder.mkdir(parents=True,exist_ok=True)
                files=[]
                stored=self._freeze(result,folder,files) if result is not None else {'error':error}
                if capture and ok:
                    for file in capture():
                        file=Path(file).resolve()
                        if not file.is_file():raise NeedsScope('原始证据未生成：'+str(file))
                        self._freeze(str(file),folder,files)
                row={'schema':SCHEMA,'check_id':cid,'binding':plan['binding'],'roots':plan['roots'],
                     'passed':ok,'executed_at':stamp(),'seconds':elapsed,'result':stored,'files':files,'error':error}
                with self.db:self.db.execute('INSERT OR REPLACE INTO records VALUES(?,?,?)',(plan['key'],cid,canonical(row)))
            finally:
                with self.db:self.db.execute('DELETE FROM active WHERE check_id=? AND token=?',(cid,token))
            self.event(cid,'passed' if ok else 'failed',seconds=elapsed,domain=plan['domain'],label=plan['label'],key=plan['key'],error=error)
            print('节点｜%s · %s：%s，用时 %.2f 秒'%(DOMAINS[plan['domain']],plan['label'],'通过' if ok else '未通过',elapsed),file=sys.stderr)
        return stored,dict(reused=False,key=plan['key'],seconds=elapsed)

    def execute_batch(self, plans, fn, passed, *, verify_inputs=None):
        """One browser batch for the missing/changed independent units, never one boot per cache row.

        fn receives check IDs and returns {id: result}; partial failures remain partial.
        The wall time is a shared batch cost; do not sum the nested per-record times.
        All plans are resolved BEFORE any browser starts.
        """
        bad=[p for p in plans if p['action'] not in ('run','reuse')]
        if bad:raise NeedsScope('；'.join(p['check_id']+'：'+p['why'] for p in bad))
        output={};meta={};batch={};actual=[]
        def visit(i):
            if i == len(plans):
                if actual:batch.update(fn(actual))
                return
            p=plans[i];cid=p['check_id']
            def execute_one():
                actual.append(cid);visit(i+1)
                if cid not in batch:raise NeedsScope('检查器未返回计划中的节点：'+cid)
                return batch[cid]
            result,detail=self.execute(p,execute_one,passed,
                verify_inputs=(lambda:verify_inputs(p)) if verify_inputs else None)
            output[cid]=result;meta[cid]=detail
            if detail['reused']:visit(i+1)
        visit(0)
        return output,meta

    def status(self):
        events=[json.loads(x[0]) for x in self.db.execute('SELECT data FROM events ORDER BY seq')]
        last={}
        for e in events:last[e['check_id']]=e
        return {'schema':SCHEMA,'project':str(self.project),'nodes':list(last.values()),
                'executions':sum(e['state']=='running' for e in events),'reuses':sum(e['state']=='reused' for e in events),
                'events':events}

    def export(self, folder):
        """Portable original records for the completed-source+test-ZIP entry route."""
        folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=True)
        rows=[json.loads(x[0]) for x in self.db.execute('SELECT data FROM records')]
        paths={}
        for row in rows:
            if row.get('passed') and not self._evidence_valid(row):raise NeedsScope('原证据丢失，不能导出为有效检查：'+row['check_id'])
            for file in row.get('files',[]):
                p=Path(file['path']);rel='evidence/'+file['sha256']+p.suffix
                target=folder/rel;target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(p,target);paths[str(p)]='${EVIDENCE}/'+rel
        def portable(v):
            if isinstance(v,dict):return {k:portable(x) for k,x in v.items()}
            if isinstance(v,list):return [portable(x) for x in v]
            return paths.get(v,v) if isinstance(v,str) else v
        data={'schema':'check-ledger-bundle.v1','source_project':str(self.project),'records':portable(rows)}
        file=folder/'records.json';file.write_text(canonical(data)+'\n')
        return {'bundle':str(folder),'records':len(rows),'sha256':sha(file.read_bytes())}

    def import_bundle(self, folder):
        folder=Path(folder).resolve();data=json.loads((folder/'records.json').read_text())
        if data.get('schema')!='check-ledger-bundle.v1':raise NeedsScope('检查记录包格式不兼容')
        def resolve(v):
            if isinstance(v,dict):return {k:resolve(x) for k,x in v.items()}
            if isinstance(v,list):return [resolve(x) for x in v]
            if isinstance(v,str) and v.startswith('${EVIDENCE}/'):
                p=(folder/v[len('${EVIDENCE}/'):]).resolve()
                if folder not in p.parents:raise NeedsScope('证据路径越界')
                return str(p)
            return v
        rows=resolve(data.get('records',[]))
        # Validate all files before importing any record. Imported records are compared
        # with the CURRENT inputs by prepare(); import is not a current-build approval.
        for row in rows:
            if row.get('schema')!=SCHEMA or row.get('check_id')!=row.get('binding',{}).get('check_id'):
                raise NeedsScope('检查记录身份不匹配')
            if not self._evidence_valid(row):raise NeedsScope('检查证据缺失或字节不符：'+row['check_id'])
        for row in rows:
            key=sha(row['binding']);files=[];folder_out=self.home/'evidence'/key;folder_out.mkdir(parents=True,exist_ok=True)
            row['result']=self._freeze(row['result'],folder_out,files)
            for f in row['files']:self._freeze(f['path'],folder_out,files)
            row['files']=files;row['imported_from']=data['source_project']
            with self.db:self.db.execute('INSERT OR IGNORE INTO records VALUES(?,?,?)',(key,row['check_id'],canonical(row)))
        return {'imported':len(rows),'current_approval':False,'next':'按当前输入 plan；原时间保留，未执行检查'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project',type=Path,required=True)
    p.add_argument('command',choices=['status','scope-template','export','import'])
    p.add_argument('--out',type=Path)
    p.add_argument('--bundle',type=Path)
    a=p.parse_args()
    if a.command=='scope-template':
        data={'schema':SCOPE_SCHEMA,'checks':{},'note':'按真实资源/代码使用者登记每个检查项；不可用空依赖或只写改动文件代替依赖范围。'}
    else:
        l=Ledger(a.project)
        try:
            if a.command in ('export','import'):
                if not a.bundle:p.error('export/import requires --bundle <directory>')
                data=l.export(a.bundle) if a.command=='export' else l.import_bundle(a.bundle)
            else:data=l.status()
        finally:l.close()
    text=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
    if a.out:a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(text)
    else:print(text)
    return 0


if __name__=='__main__':raise SystemExit(main())
