"""Pre-change byte-bound method/case ownership. Pure static parsing; game JS is never run."""
import hashlib
import json
from pathlib import Path
import subprocess

SCHEMA='art-case-dependencies.v1'

def digest(obj):
    return hashlib.sha256(json.dumps(obj,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def file_sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

_PARSER=r'''
const fs=require('fs'),acorn=require(process.argv[1]),crypto=require('crypto');
const input=JSON.parse(fs.readFileSync(0,'utf8')),text=input.text;
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
let ast;try{ast=acorn.parse(text,{ecmaVersion:'latest',sourceType:'script'});}catch(e){ast=acorn.parse(text,{ecmaVersion:'latest',sourceType:'module'});}
const found=new Map(),containers=[];
function walk(n,visit){if(!n||typeof n!=='object'||!n.type)return;visit(n);for(const v of Object.values(n)){if(Array.isArray(v))v.forEach(x=>walk(x,visit));else if(v&&v.type)walk(v,visit);}}
const named=n=>(n.type==='Property'||n.type==='MethodDefinition')&&!n.computed&&['FunctionExpression','ArrowFunctionExpression'].includes(n.value?.type);
walk(ast,n=>{const props=n.type==='ObjectExpression'?n.properties:n.type==='ClassBody'?n.body:null;if(!props)return;
 const methods=props.filter(named);if(input.names.every(name=>methods.filter(p=>(p.key.name??p.key.value)===name).length===1))containers.push(methods);});
if(containers.length!==1)throw Error('method owner container missing/ambiguous');
for(const n of containers[0]){const name=n.key.name??n.key.value;if(typeof name==='string'){if(!found.has(name))found.set(name,[]);found.get(name).push(n);}}
const names=new Set(found.keys()),selected=[];
for(const name of input.names){const hits=found.get(name)||[];if(hits.length!==1)throw Error('method missing/ambiguous: '+name);selected.push([name,hits[0]]);}
selected.sort((a,b)=>a[1].start-b[1].start);
for(let i=1;i<selected.length;i++)if(selected[i][1].start<selected[i-1][1].end)throw Error('overlapping owned methods');
const methods={},references={},dynamic=[];
for(const [name,hits] of found){if(hits.length!==1){dynamic.push('ambiguous method '+name);continue;}
 const n=hits[0],aliases=new Set(['this']);walk(n.value,k=>{if(k.type==='VariableDeclarator'&&k.init?.type==='ThisExpression'&&k.id.type==='Identifier')aliases.add(k.id.name);});
 const refs=new Set();walk(n.value,k=>{if(k.type!=='MemberExpression')return;const own=k.object.type==='ThisExpression'||k.object.type==='Identifier'&&aliases.has(k.object.name);if(!own)return;
 if(k.computed){dynamic.push(name+': computed method/field access');return;}if(names.has(k.property.name))refs.add(k.property.name);});
 references[name]=[...refs].sort();}
let outside='',cursor=0;for(const [name,n]of selected){outside+=text.slice(cursor,n.start)+'<owned:'+name+'>';cursor=n.end;methods[name]=hash(text.slice(n.start,n.end));}outside+=text.slice(cursor);
console.log(JSON.stringify({file:hash(text),shared:hash(outside),methods,references,dynamic}));
'''

def project_file(root,name):
    p=Path(root)/name
    if not isinstance(name,str) or Path(name).is_absolute() or '..' in Path(name).parts or p.is_symlink():
        raise ValueError('unsafe dependency path')
    if not p.is_file():raise ValueError('missing dependency file: '+name)
    # Reject a symlink in any parent as well.
    if p.resolve()!=p.absolute():raise ValueError('symbolic dependency ancestor: '+name)
    return p

def projection(root,entry):
    p=project_file(root,entry['path'])
    return projection_bytes(p.read_bytes(),entry)

def projection_bytes(raw,entry):
    if entry['kind']=='asset':return {'file':hashlib.sha256(raw).hexdigest()}
    if entry['kind']!='methods':raise ValueError('unknown dependency kind')
    names=[m['name'] for m in entry['methods']]
    parser=Path(__file__).with_name('vendor')/'acorn.cjs'
    proc=subprocess.run(['node','-e',_PARSER,str(parser)],input=json.dumps({'text':raw.decode('utf-8'),'names':names}),capture_output=True,text=True,timeout=60)
    if proc.returncode:raise ValueError('static method closure unknown: '+proc.stderr.strip().splitlines()[0])
    return json.loads(proc.stdout)

def validate(contract,case_ids):
    if contract.get('schema')!=SCHEMA or set(contract.get('cases',[]))!=set(case_ids):raise ValueError('case dependency matrix mismatch')
    inputs=contract.get('case_inputs',{})
    if set(inputs)!=set(case_ids):raise ValueError('every case needs an explicit input-state contract before capture')
    for spec in inputs.values():
        if spec.get('mode') not in ('origin_bound','fresh') or not spec.get('basis') or not isinstance(spec.get('external_inputs'),list):
            raise ValueError('case inputs require mode, reviewed basis and explicit external inputs')
    seen=set();units={}
    for entry in contract.get('files',[]):
        key=(entry.get('domain'),entry.get('path'))
        if key in seen or key[0] not in ('source','export'):raise ValueError('duplicate/unknown dependency domain')
        seen.add(key)
        if not isinstance(entry.get('unit'),str) or not entry['unit']:raise ValueError('source/export unit identity required')
        units.setdefault(entry['unit'],{}).setdefault(entry['domain'],[]).append(entry)
        owners=entry.get('methods') if entry.get('kind')=='methods' else [entry]
        if not isinstance(owners,list) or not owners:raise ValueError('missing exact ownership')
        if entry.get('kind')=='methods' and len({m.get('name') for m in owners})!=len(owners):raise ValueError('duplicate method ownership')
        for owner in owners:
            cases=owner.get('cases')
            if not owner.get('basis') or not isinstance(cases,list) or not cases or not set(cases)<=set(case_ids):raise ValueError('ownership needs known cases and reviewed basis')
    if not seen:raise ValueError('empty dependency contract')
    for unit,pair in units.items():
        if set(pair)!={'source','export'} or any(len(v)!=1 for v in pair.values()):raise ValueError('unit needs exactly one source/export pair: '+unit)
        a,b=pair['source'][0],pair['export'][0]
        owners=lambda e:{m['name']:sorted(m['cases']) for m in e['methods']} if e['kind']=='methods' else sorted(e['cases'])
        if a['kind']!=b['kind'] or owners(a)!=owners(b):raise ValueError('source/export ownership mismatch: '+unit)

def snapshot_views(contract,project,build):
    return {entry['domain']+':'+entry['path']:projection(project if entry['domain']=='source' else build,entry) for entry in contract['files']}

def affected_cases(contract,before,after,changed_files):
    """Unmapped/shared edits expand once; an unparseable/dynamic closure stays unknown."""
    all_cases=set(contract['cases']);affected={c for c,spec in contract['case_inputs'].items() if spec['mode']=='fresh' or spec['external_inputs']}
    reasons=['fresh/externally driven state: '+c for c in sorted(affected)];unknown=[];mapped=set();changed_units={}
    for entry in contract['files']:
        domain,path=entry['domain'],entry['path'];key=domain+':'+path;mapped.add((domain,path))
        if path not in changed_files.get(domain,[]):continue
        a,b=before.get(key),after.get(key)
        if not a or not b:unknown.append('missing dependency projection: '+key);continue
        if entry['kind']=='asset':
            affected.update(entry['cases']);changed_units.setdefault(entry['unit'],{})[domain]={'asset'};continue
        if a['shared']!=b['shared']:
            affected.update(all_cases);reasons.append('shared bytes changed: '+key);continue
        changed={name for name in a['methods'] if a['methods'][name]!=b['methods'].get(name)}
        changed_units.setdefault(entry['unit'],{})[domain]=changed
        if changed and (a.get('dynamic') or b.get('dynamic')):
            unknown.append('dynamic/ambiguous method closure: '+key);continue
        refs={name:set(a.get('references',{}).get(name,[]))|set(b.get('references',{}).get(name,[]))
              for name in set(a.get('references',{}))|set(b.get('references',{}))}
        dependents=set(changed)
        while True:
            expanded=dependents|{name for name,deps in refs.items() if deps&dependents}
            if expanded==dependents:break
            dependents=expanded
        owners={m['name']:m for m in entry['methods']}
        if dependents-set(owners):
            affected.update(all_cases);reasons.append('unowned method consumer: '+key)
        else:
            for name in dependents:affected.update(owners[name]['cases'])
    for domain in ('source','export'):
        for name in changed_files.get(domain,[]):
            if (domain,name) not in mapped:
                affected.update(all_cases);reasons.append('unmapped shared file: '+domain+':'+name)
    for unit,domains in changed_units.items():
        if domains.get('source',set())!=domains.get('export',set()):unknown.append('source/export method changes do not correspond: '+unit)
    for unit in {e['unit'] for e in contract['files'] if e['kind']=='asset'}:
        pair={e['domain']:e for e in contract['files'] if e['unit']==unit}
        keys={d:d+':'+e['path'] for d,e in pair.items()}
        if any(views.get(keys['source'],{}).get('file')!=views.get(keys['export'],{}).get('file') for views in (before,after)):
            unknown.append('source/export asset bytes do not correspond: '+unit)
    if unknown:affected.update(all_cases)
    return {'affected_cases':sorted(affected),'unaffected_cases':sorted(all_cases-affected),
            'unknown':unknown,'shared_expansions':reasons}
