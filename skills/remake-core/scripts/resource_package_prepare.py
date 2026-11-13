#!/usr/bin/env python3
"""Prepare source resource ownership before art production; calibrate first Native bytes.

No game/browser execution. Cocos2.4 ordinary bundles and exact supported startup
are applied; Cocos3 consumes actual configuration plus reviewed finite adapters. Unknown routing is an exact mapping task;
never a request to repeat a gameplay/art matrix. See resource-package-prepare.md.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from functools import wraps
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path: sys.path.insert(0, str(HERE))
import audit_package_estimate as estimate
import first_screen
import startup_budget
from preparation_cache import project_lock

SCHEMA = 'resource-package-prepare.v1'
PLAN_SCHEMA = 'resource-package-plan.v1'
HOME = Path('.tiktok-kit/resource-package')
PLAN = Path('docs/startup/resource-package-plan.json')
MAIN_LIMIT = 4_000_000
FIRST_LIMIT = 10 * 1024 * 1024
SKIP = {'.git', 'node_modules', '__pycache__'}
ADAPTER = 'assets/scripts/generated/ResourcePackageLoader.js'
MARKER = '// resource-package-routing.v1\n'


def sha(data): return hashlib.sha256(data).hexdigest()
def encoded(data): return (json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':'))+'\n').encode()
def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def save(path, data):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name+'.tmp'); temp.write_bytes(encoded(data)); os.replace(temp, path)

def relative(value, *, assets=False):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value:
        raise ValueError('portable relative path required: '+repr(value))
    p = PurePosixPath(value)
    if p.is_absolute() or any(x in ('', '.', '..') for x in value.split('/')):
        raise ValueError('unsafe relative path: '+value)
    if assets and (len(p.parts)<2 or p.parts[0]!='assets'):
        raise ValueError('asset directory must be below assets/: '+value)
    return value

def _files(project):
    for root in ('assets', 'settings', 'build-templates', 'profiles'):
        base = project/root
        if base.exists():
            for p in sorted(base.rglob('*')):
                rel = p.relative_to(project)
                if SKIP & set(rel.parts): continue
                if p.is_symlink(): raise ValueError('resource input symlink needs mapping: '+rel.as_posix())
                if p.is_file(): yield rel.as_posix(), p
    for root in ('project.json', 'package.json'):
        p=project/root
        if p.is_file(): yield root,p

def inputs(project): return {rel:sha(p.read_bytes()) for rel,p in _files(project)}

def tools():
    names = ('resource_package_prepare.py','resource_package_prepare.cjs','first_screen.py',
             'audit_package_estimate.py','startup_budget.py','scan_runtime_resources.cjs',
             'parse_package_requires.cjs','preparation_cache.py','vendor/acorn.cjs',
             'tiktok_finalize_steps/__init__.py','tiktok_finalize_steps/startup.py',
             'upload_size_gate.py','package_gates/__init__.py','package_gates/startup.py','project_qa.py')
    out={n:sha((HERE/n).read_bytes()) for n in names}
    from tiktok_finalize_steps import load_manifest
    manifest=load_manifest()
    for rel in ('KIT_MANIFEST.json','parts/ResLoader.js',*manifest.included): out['kit/'+rel]=sha((manifest.kit_dir/rel).read_bytes())
    from tiktok_finalize_steps.startup import startup_part
    name,part=startup_part(manifest)
    for spec in [part.get('file',{}),*part.get('extra_files',[])]:
        if spec.get('src'):out['kit/'+spec['src']]=sha((manifest.kit_dir/spec['src']).read_bytes())
    needed=set(re.findall(r"require\(['\"]\./([A-Za-z0-9_-]+)(?:\.js)?['\"]\)",(manifest.kit_dir/part['file']['src']).read_text()))
    for p in manifest.parts.values():
        spec=p.get('file',{})
        if spec.get('dest') in {x+'.js' for x in needed}:out['kit/'+spec['src']]=sha((manifest.kit_dir/spec['src']).read_bytes())
    return out

def _mapping(task, **detail): return {'status':'mapping_required','task':task,**detail}

def result_contract(fn):
    @wraps(fn)
    def call(*args, **kwargs):
        try:out=fn(*args, **kwargs)
        except (ValueError,KeyError,TypeError,OSError,subprocess.SubprocessError,AttributeError) as error:
            out={'schema':SCHEMA,'status':'mapping_required','tasks':[_mapping('resource_contract',detail=str(error))]}
        out['passed']=out.get('status') in ('prepared','calibrated')
        tasks=out.get('tasks') or ([] if out['passed'] else [out])
        out['blocks']=[{'id':'resource_'+t.get('task','mapping'), 'message':t.get('required') or t.get('detail') or t.get('task','resource mapping'),
                        'scope':{k:v for k,v in t.items() if k not in ('status','task','schema','passed','blocks','next_action','elapsed_seconds','reused')}} for t in tasks]
        out['next_action']=('continue_current_stage' if out['passed'] else
            'current_agent: resolve listed resource mappings, prepare only the changed resource groups, then continue; do not ask user to say continue or rerun unrelated tests')
        return out
    return call

def _scan(project):
    scripts={rel:p.read_text(encoding='utf-8') for rel,p in _files(project)
             if p.suffix in ('.js','.ts') and rel!=ADAPTER and '/tiktok-platform/' not in rel
             and '/generated/' not in rel and rel.startswith('assets/')}
    js={r:s for r,s in scripts.items() if r.endswith('.js')}
    node=first_screen.node_bin()
    if not node: return scripts,{},[_mapping('install_or_locate_node_for_resource_ast')]
    result=subprocess.run([node,str(HERE/'scan_runtime_resources.cjs')],input=json.dumps({'files':js}),
                          text=True,capture_output=True,timeout=30)
    if result.returncode: return scripts,{},[_mapping('resource_ast_parse',detail=result.stderr[-1500:])]
    data=json.loads(result.stdout)
    edit=subprocess.run([node,str(HERE/'resource_package_prepare.cjs')],input=json.dumps({'files':js}),text=True,capture_output=True,timeout=30)
    if edit.returncode:return scripts,data,[_mapping('resource_edit_ast',detail=edit.stderr[-1000:])]
    data['edits']=json.loads(edit.stdout)
    return scripts,data,[]

def _owner_plan(project, supplied, old):
    if supplied is None and (project/PLAN).is_file(): supplied=read(project/PLAN)
    plan=supplied or (old or {}).get('plan') or {'schema':PLAN_SCHEMA,'bundles':[],'deferred_groups':[]}
    plan=json.loads(json.dumps(plan))
    if plan.get('schema')!=PLAN_SCHEMA:raise ValueError('resource package plan schema required')
    plan.setdefault('bundles',[]);plan.setdefault('deferred_groups',[])
    for g in plan['deferred_groups']:
        if not any(b.get('directory')==g.get('destination') for b in plan['bundles']):
            plan['bundles'].append({'directory':g['destination'],'name':g['name'],'load':'deferred','independent':False})
    if estimate.engine_major(project)[1]=='2' and (project/'assets/resources').is_dir() and not any(x.get('directory')=='assets/resources' for x in plan['bundles']):
        plan['bundles'].insert(0,{'directory':'assets/resources','name':'resources','load':'startup','independent':False})
    return plan

def _meta(project, directory, name):
    path=project/(directory+'.meta')
    d=read(path) if path.is_file() else {'ver':'1.1.2','uuid':str(uuid.uuid5(uuid.NAMESPACE_URL,'cocos-resource-package:'+directory)),'subMetas':{}}
    if not isinstance(d,dict) or not isinstance(d.get('uuid'),str):raise ValueError('folder meta needs UUID: '+directory)
    compression=d.get('compressionType') or {}
    if not isinstance(compression,dict):raise ValueError('compressionType needs per-platform object: '+directory)
    original=json.loads(json.dumps(d))
    d.update(isBundle=True,bundleName=name,compressionType={**compression,'bytedance':'subpackage'})
    return path,(path.read_bytes() if d==original and path.is_file() else encoded(d))

def _kit_changes(project, version):
    from tiktok_finalize_steps import load_manifest
    from tiktok_finalize_steps.startup import kit_main_bytes,startup_part
    manifest=load_manifest();name,part=startup_part(manifest)
    main=kit_main_bytes(manifest);target=project/'build-templates/bytedance/main.js'
    if version!='2.4.15':
        # Keep the original editor bootstrap for other supported 2.4 versions.
        # Native calibration must prove its actual bundle chain before approval.
        return {},[]
    if target.is_file() and sha(target.read_bytes()) not in manifest.all_versions(name):
        return {},[_mapping('boot_integration',source=target.relative_to(project).as_posix(),sha256=sha(target.read_bytes()),
                            required='map existing startup to bundle resources before launch; preserve its behavior')]
    changes={target:main}
    # The kit template has static sibling requires; preserve exactly the shipped part bytes.
    needed=set(re.findall(r"require\(['\"]\./([A-Za-z0-9_-]+)(?:\.js)?['\"]\)",main.decode()))
    specs=list(part.get('extra_files',[]))
    for n,p in manifest.parts.items():
        spec=p.get('file',{})
        if spec.get('dest') in {x+'.js' for x in needed}:specs.append(spec)
    for dest in sorted(needed):
        filename=dest+'.js';spec=next((x for x in specs if x.get('dest')==filename),None)
        if not spec:return {},[_mapping('kit_static_dependency',required=filename)]
        data=(manifest.kit_dir/spec['src']).read_bytes()
        if sha(data)!=spec.get('sha256'):raise ValueError('kit dependency differs: '+filename)
        path=target.parent/filename
        if path.is_file() and path.read_bytes()!=data:return {},[_mapping('custom_template_dependency',source=path.relative_to(project).as_posix())]
        changes[path]=data
    return changes,[]

def _adapter(groups):
    """Small callback bridge; actual bundle progress/retry/foreground timing stays in shipped ResLoader."""
    mapping=[{'prefix':g['source'][len('assets/resources/'):], 'bundle':g['name']} for g in groups]
    loader=os.path.relpath('assets/tiktok-platform/ResLoader',str(Path(ADAPTER).parent)).replace(os.sep,'/')
    return (MARKER+"'use strict';\nvar Res = require("+json.dumps(loader)+");\nvar routes = "+json.dumps(mapping)+";\n"+r'''
function route(method, args) {
  var cc = globalThis.cc, path = args[0], legacy = method === 'loadRes' || method === 'loadResDir';
  var receiver = legacy ? cc.loader : cc.resources;
  var original = receiver[method];
  if (typeof path !== 'string') return original.apply(receiver,args);
  var hit = routes.find(function(r){return path === r.prefix || path.indexOf(r.prefix + '/') === 0;});
  if (!hit) return original.apply(receiver,args);
  var callback = args[args.length-1];
  if (typeof callback !== 'function') throw new TypeError('resource route needs the original completion callback');
  var actual = method === 'loadRes' ? 'load' : method === 'loadResDir' ? 'loadDir' : method;
  var forwarded = args.slice(); forwarded[0] = path.slice(hit.prefix.length).replace(/^\//,'');
  Res.loadBundle(hit.bundle).then(function(bundle) {bundle[actual].apply(bundle,forwarded);}, function(error){callback(error);});
}
var api = {};
['load','loadDir','preload','preloadDir','loadRes','loadResDir'].forEach(function(method){
  api[method]=function(){return route(method,Array.prototype.slice.call(arguments));};
});
module.exports=api;
''').encode()

def _move_plan(project,plan,scripts,scan,home):
    groups=plan['deferred_groups'];issues=[];moves=[];changes={}
    for group in groups:
        src=relative(group['source'],assets=True);dst=relative(group['destination'],assets=True)
        if not src.startswith('assets/resources/') or src==dst or dst.startswith(src+'/') or src.startswith(dst+'/'):
            raise ValueError('deferred group must leave resources as one non-overlapping directory')
        if len(PurePosixPath(dst).parts)!=2:raise ValueError('deferred bundle destination must be top-level under assets')
        if any(x==src or x.startswith(src+'/') for x in home):issues.append(_mapping('group_has_first_screen_dependency',source=src))
        if (project/src).is_dir():
            source_files=[p for p in (project/src).rglob('*') if p.is_file()]
            if any(p.suffix in ('.js','.ts','.fire','.scene') for p in source_files):
                issues.append(_mapping('group_contains_code_or_scene',source=src));continue
            if (project/dst).exists():
                prior=project/HOME/'prepared.json'
                prior_groups=(read(prior).get('plan',{}).get('deferred_groups',[]) if prior.is_file() else [])
                if group not in prior_groups:issues.append(_mapping('destination_exists',source=src,destination=dst));continue
                # Newly imported files in a previously assigned namespace follow that same group.
                # No asset or its .meta is rewritten, and conflicting existing bytes are refused.
                for file in source_files:
                    target=project/dst/file.relative_to(project/src)
                    if target.is_file() and target.read_bytes()!=file.read_bytes():
                        issues.append(_mapping('new_resource_collision',source=file.relative_to(project).as_posix(),destination=target.relative_to(project).as_posix()))
                    else:changes[target]=file.read_bytes();changes[file]=None
                if Path(str(project/src)+'.meta').is_file():changes[Path(str(project/src)+'.meta')]=None
            else:
                if not Path(str(project/src)+'.meta').is_file():issues.append(_mapping('folder_meta_missing',source=src));continue
                moves.append((src,dst))
        elif not (project/dst).is_dir():issues.append(_mapping('group_directory_missing',source=src,destination=dst))
        entry={'directory':dst,'name':group['name'],'load':'deferred','independent':False}
        if not any(b.get('directory')==dst for b in plan['bundles']):plan['bundles'].append(entry)
    if not groups:return changes,moves,issues
    # Refuse unexplained aliases/paths before any move. The AI repairs only these sites.
    for item in scan.get('escapes',[]):issues.append(_mapping('loader_alias_or_dynamic_code',**item))
    for item in scan.get('sites',[]):
        code=scripts.get(item['source'],'')
        known_bridge=(code.startswith(MARKER) and str(item.get('expression','')).startswith('__resourcePackage.'))
        if item.get('unknown_receiver') and not known_bridge:
            issues.append(_mapping('unknown_loader_receiver',source=item['source'],line=item.get('line'),expression=item.get('expression')))
        if item.get('bundles') and 'resources' in item['bundles'] and not item.get('paths'):
            issues.append(_mapping('dynamic_resource_domain',source=item['source'],line=item.get('line'),expression=item.get('expression')))
    for rel,code in scripts.items():
        if rel.endswith('.ts') and first_screen.RAW_LOAD.search(code):issues.append(_mapping('typescript_resource_callsite',source=rel))
    edits=scan.get('edits',{'sites':[],'errors':[]})
    issues.extend(_mapping('resource_edit_ast',**x) for x in edits['errors'])
    for site in edits['sites']:
        if not site['completion']:
            issues.append(_mapping('resource_completion_callback',source=site['source'],line=site['line'],required='map the moved resource completion callback before deferred loading; preserve caller behavior'))
    by_file={}
    for item in edits['sites']:by_file.setdefault(item['source'],[]).append(item)
    for rel,sites in by_file.items():
        code=scripts[rel]
        if '__resourcePackage' in code and MARKER not in code:issues.append(_mapping('route_identifier_collision',source=rel));continue
        for item in sorted(sites,key=lambda x:-x['start']):code=code[:item['start']]+'__resourcePackage.'+item['method']+code[item['end']:]
        req=os.path.relpath(ADAPTER[:-3],str(Path(rel).parent)).replace(os.sep,'/')
        if not req.startswith('.'):req='./'+req
        if MARKER not in code:code=MARKER+'var __resourcePackage = require('+json.dumps(req)+');\n'+code
        changes[project/rel]=code.encode()
    # If resources are loaded through an unrewritten receiver, exact sites need a mapping.
    supported={(x['source'],x['line']) for x in edits['sites']}
    for item in scan.get('sites',[]):
        if item.get('bundles') and 'resources' in item['bundles'] and (item['source'],item.get('line')) not in supported:
            issues.append(_mapping('resource_receiver_mapping',source=item['source'],line=item.get('line'),expression=item.get('expression')))
    changes[project/ADAPTER]=_adapter(groups)
    changes[project/(ADAPTER+'.meta')]=encoded({'ver':'1.0.8','uuid':str(uuid.uuid5(uuid.NAMESPACE_URL,ADAPTER)),'isPlugin':False,'subMetas':{}})
    from tiktok_finalize_steps import load_manifest
    manifest=load_manifest();path=manifest.kit_dir/'parts/ResLoader.js';data=path.read_bytes()
    if sha(data)!=manifest.files.get('parts/ResLoader.js',{}).get('sha256'):
        # Some manifests index the part source through its source-files entry.
        spec=next((p.get('file',{}) for p in manifest.parts.values() if p.get('file',{}).get('src')=='parts/ResLoader.js'),{})
        if sha(data)!=spec.get('sha256'):raise ValueError('unverified shipped ResLoader')
    target=project/'assets/tiktok-platform/ResLoader.js'
    if target.is_file() and target.read_bytes()!=data:issues.append(_mapping('existing_custom_resource_loader',source='assets/tiktok-platform/ResLoader.js'))
    changes[target]=data
    if not Path(str(target)+'.meta').exists():changes[Path(str(target)+'.meta')]=encoded({'ver':'1.0.8','uuid':str(uuid.uuid5(uuid.NAMESPACE_URL,'tiktok-platform/ResLoader')),'subMetas':{}})
    return changes,moves,issues

def _adapter_policy(project):
    import project_qa
    try:return project_qa.lookup(project,'validators','resource_package_adapter.v1')
    except ValueError as error:
        if str(error).startswith('no reviewed project QA registration'):return None
        raise


def _adapter_identity(project):
    policy=_adapter_policy(project)
    if policy is None:return None
    return {Path(p).relative_to(project).as_posix():digest for p,digest in policy['dependencies'].items()}


def _provider(project,plan,source,phase,native=None):
    import project_qa
    policy=_adapter_policy(project)
    if policy is None:return None
    before=inputs(project)
    scope=project_qa.invoke(policy,'resource_package_adapter',project=project,phase=phase,
        source_inventory=source,plan=plan,native_inventory={k:sha(v) for k,v in (native or {}).items()},native_files=dict(native or {}))
    if inputs(project)!=before:raise ValueError('reviewed resource provider must inspect only, not mutate source')
    if (not isinstance(scope,dict) or scope.get('schema')!='resource_package_adapter.v1' or
        scope.get('source_inventory_sha256')!=sha(encoded(source)) or scope.get('unknown')!=[] or
        not isinstance(scope.get('basis'),str) or not scope['basis'].strip()):
        raise ValueError('resource adapter needs actual complete source inventory digest, basis and unknown:[]; true is not evidence')
    if phase=='native' and scope.get('native_inventory_sha256')!=sha(encoded({k:sha(v) for k,v in native.items()})):
        raise ValueError('resource adapter Native inventory does not match actual artifact bytes')
    return scope


def _pointer(data,path):
    if not isinstance(path,list) or not path:raise ValueError('adapter config JSON pointer must be an explicit nonempty array')
    for part in path:data=data[part]
    return data


def _source3_bundles(project,scope):
    roots={}
    for meta in sorted((project/'assets').rglob('*.meta')):
        folder=meta.with_suffix('')
        if not folder.is_dir():continue
        m=read(meta);u=m.get('userData') or {};owner=u if u.get('isBundle') is True else m
        if not (owner.get('isBundle') is True or folder==project/'assets/resources'):continue
        mode=owner.get('compressionType') or {};kind=mode.get('bytedance-mini-game',mode.get('bytedance')) if isinstance(mode,dict) else None
        directory=folder.relative_to(project).as_posix();name='resources' if directory=='assets/resources' else owner.get('bundleName') or folder.name
        roots[directory]={'directory':directory,'name':name,'subpackage':kind=='subpackage','independent':False}
    for spec in (scope or {}).get('bundles',[]):
        directory=relative(spec['directory'],assets=True);name=spec['name'];fact=spec['config'];config=project/relative(fact['file'])
        if not (project/directory).is_dir() or not config.is_file():raise ValueError('adapter bundle/config directory missing: '+directory)
        if fact['file'] not in inputs(project):raise ValueError('adapter builder config must be an actual tracked production input')
        data=read(config)
        if (_pointer(data,fact['name_pointer'])!=name or _pointer(data,fact['mode_pointer'])!='subpackage' or
            _pointer(data,fact['enabled_pointer']) is not True):raise ValueError('adapter bundle declaration differs from actual name/mode/enabled configuration: '+directory)
        roots[directory]={'directory':directory,'name':name,'subpackage':True,'independent':False}
    names=set()
    for spec in roots.values():
        name=spec['name']
        if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9_.-]+',name) or name.casefold() in names:raise ValueError('duplicate/nonportable actual 3.x bundle name')
        names.add(name.casefold())
    return roots


def _prepare3(project,selected,old,fingerprints,current,started,read_only=False):
    """Read real3.x configuration; never run a2.x mutator or pretend an adapter bool is approval."""
    scope=_provider(project,selected,current,'source');identity=_adapter_identity(project)
    roots=_source3_bundles(project,scope);issues=[]
    if selected.get('deferred_groups'):
        for group in selected['deferred_groups']:
            if (project/group['source']).exists() and any((project/group['source']).rglob('*')):
                issues.append(_mapping('engine3_group_not_migrated',source=group['source'],destination=group['destination'],required='current AI: migrate this exact group and its3.x loading calls, preserving metadata, then prepare again'))
    for spec in selected['bundles']:
        actual=roots.get(spec['directory'])
        if spec.get('independent') is True:issues.append(_mapping('independent_entry',directory=spec['directory']))
        if not actual or not actual['subpackage'] or actual['name']!=spec['name']:
            issues.append(_mapping('engine3_actual_bundle_config',directory=spec['directory'],required='current AI: set actual Creator3 userData bundle name and target subpackage compression, or register the exact actual builder config pointers with resource_package_adapter.v1'))
    fs=first_screen.analyze(project,'localize',selected.get('boot_scene'),selected.get('home_scene'))
    home_scripts={x['file'] for x in fs['home_needs']['files'] if x.get('kind')=='script'}
    early=set(scope['startup_bundles']) if scope is not None and isinstance(scope.get('startup_bundles'),list) else ({'resources'} if any(x['name']=='resources' for x in roots.values()) else set())
    for item in fs['home_needs']['files']:
        owners=[b for directory,b in roots.items() if item['file'].startswith(directory+'/')]
        if owners:
            owner=max(owners,key=lambda b:len(b['directory']))
            if owner['subpackage']:early.add(owner['name'])
    unknown=[]
    for rel in home_scripts:
        text=(project/rel).read_text(encoding='utf-8');matches=list(first_screen.LOAD_BUNDLE.finditer(text))
        for m in matches:
            if first_screen.runs_before_home(text,m.start(),fs['boot_scene']!=fs['home_scene']):early.add(next(x for x in m.groups() if x))
        for m in re.finditer(r'\bloadBundle\s*\(',text):
            if any(x.start()<=m.start()<x.end() for x in matches):continue
            if first_screen.runs_before_home(text,m.start(),fs['boot_scene']!=fs['home_scene']):
                unknown.append({'source':rel,'line':text.count('\n',0,m.start())+1})
    resolved={}
    for item in (scope or {}).get('resolved_sites',[]):
        rel=relative(item['source']);key=(rel,item['line'])
        if item.get('source_sha256')!=current.get(rel) or not isinstance(item.get('bundles'),list) or not item['bundles']:
            raise ValueError('adapter resolved site must bind actual source bytes and finite bundle names')
        resolved[key]=item['bundles']
    for item in unknown:
        key=(item['source'],item['line'])
        if key in resolved:early.update(resolved[key])
        else:issues.append(_mapping('engine3_dynamic_startup_bundle',**item,required='current AI: register a reviewed resource_package_adapter.v1 provider resolving this finite bundle domain from current code/config; then prepare again'))
    early.update((scope or {}).get('startup_bundles',[]))
    known_names={x['name'] for x in roots.values()}|{'main','internal'}
    if not early<=known_names:issues.append(_mapping('engine3_unknown_bundle_names',bundles=sorted(early-known_names)))
    references=estimate.referenced_uuids(project);rows=[]
    for rel,path in _files(project):
        if not rel.startswith('assets/') or path.suffix=='.meta':continue
        owners=[b for directory,b in roots.items() if rel.startswith(directory+'/')]
        owner=max(owners,key=lambda b:len(b['directory'])) if owners else None
        if owner is None and path.suffix not in ('.fire','.scene','.js','.ts') and not estimate.asset_uuids(path)&references:continue
        rows.append({'file':rel,'bytes':startup_budget.counted_bytes(path),'bundle':owner['name'] if owner else 'main','subpackage':bool(owner and owner['subpackage'])})
    fixed=startup_budget.fixed_bytes(project);extra=project/'build-templates/bytedance-mini-game'
    extra_bytes=sum(p.stat().st_size for p in estimate.files(extra)) if extra.is_dir() else 0
    fixed_bytes=sum(fixed.values())+extra_bytes
    main=sum(x['bytes'] for x in rows if not x['subpackage'])+fixed_bytes
    first=main+sum(x['bytes'] for x in rows if x['subpackage'] and x['bundle'] in early)
    total=sum(x['bytes'] for x in rows)+fixed_bytes
    budget={'main':{'bytes':main,'limit_bytes':MAIN_LIMIT,'basis':'source_estimate_actual3_bundle_metadata','passed':main<=MAIN_LIMIT},
            'first_download':{'bytes':first,'limit_bytes':FIRST_LIMIT,'basis':'source_estimate_actual3_startup_union','passed':first<=FIRST_LIMIT},
            'total':{'bytes':total,'limit_bytes':estimate.TOTAL_LIMIT}}
    if main>MAIN_LIMIT:issues.append(_mapping('engine3_main_budget',bytes=main,required='current AI: configure the actual deferred group in Creator3 metadata/builder config and its actual load call, then prepare/register the adapter; no2.x template'))
    if first>FIRST_LIMIT:issues.append(_mapping('engine3_first_budget',bytes=first,startup_bundles=sorted(early),required='current AI: fix only identified startup dependencies; keep finite current loading evidence'))
    if total>estimate.TOTAL_LIMIT:issues.append(_mapping('engine3_total_budget',bytes=total))
    effective=json.loads(json.dumps(selected));effective['bundles']=[{'directory':x['directory'],'name':x['name'],'load':'startup' if x['name'] in early else 'deferred','independent':False} for x in roots.values() if x['subpackage']]
    result={'schema':SCHEMA,'status':('needs_prepare' if read_only else 'mapping_required') if issues else 'prepared','tasks':issues,'engine':estimate.engine_major(project)[0],
            'plan':effective,'requested_plan':effective,'adapter_identity':identity,'inputs':current,'tools':fingerprints,'budget':budget,'first_download_bundles':sorted(early),
            'boot_policy':'actual3_source_metadata_then_native_boot_graph','changes':[],'moves':[],'mutated':False,'reused':False,'elapsed_seconds':time.monotonic()-started,
            'runtime_boundary':'Read-only actual3 source configuration and static ownership; actual Native bytes/boot graph still required; no runtime acceptance'}
    if not issues:save(project/HOME/'prepared.json',result)
    return result


@result_contract
def refresh_current(project):
    """Refresh proof only. Assets/settings/templates and source-finalize binding remain byte-identical."""
    project=Path(project).resolve()
    with project_lock(project):
        before=inputs(project)
        result=prepare(project,_read_only=True)
        if inputs(project)!=before:raise ValueError('read-only resource refresh modified production source')
        if result.get('status')=='mapping_required':result['status']='needs_prepare'
        return result


def _native3(project,prepared,files,declared,prehome):
    settings_path='src/settings.json';scope=None
    if settings_path not in files:
        candidates=[p for p in files if re.fullmatch(r'src/settings\.[0-9a-fA-F]+\.json',p)]
        if len(candidates)==1:settings_path=candidates[0]
        else:
            scope=_provider(project,prepared['plan'],prepared['inputs'],'native',files)
            settings_path=relative((scope or {}).get('settings_file','src/settings.json'))
            if settings_path not in files:raise ValueError('3.x actual settings missing: reviewed resource adapter needs settings_file bound to the exact actual Native JSON')
    settings=json.loads(files[settings_path].decode('utf-8-sig'));assets=settings.get('assets') or {}
    names=settings.get('subpackages',assets.get('subpackages',[]));versions=settings.get('bundleVers',assets.get('bundleVers',{}))
    if not isinstance(names,list) or not all(isinstance(x,str) for x in names) or not set(names)<=set(declared):raise ValueError('3.x actual engine subpackages differ from game.json')
    for spec in prepared['plan']['bundles']:
        name=spec['name']
        if name not in names:raise ValueError('3.x source bundle absent from actual engine subpackages: '+name)
        root=declared[name]['root'].rstrip('/')+'/';version=versions.get(name)
        config=root+('config.'+str(version)+'.json' if version else 'config.json')
        if config not in files or json.loads(files[config].decode('utf-8-sig')).get('name')!=name:raise ValueError('3.x actual selected bundle config mismatch: '+config)
    preload=assets.get('preloadBundles',[])
    if not isinstance(preload,list) or any(not isinstance(x,dict) or not isinstance(x.get('bundle'),str) for x in preload):raise ValueError('3.x actual preloadBundles must identify finite bundles')
    requested={x['bundle'] for x in preload}
    for name in requested:
        if name in declared:
            root=declared[name]['root'].rstrip('/')+'/';prehome['subpackages'][root]=sum(len(v) for k,v in files.items() if k.startswith(root))
    node=first_screen.node_bin()
    probe=subprocess.run([node,str(HERE/'resource_package_prepare.cjs')],input=json.dumps({'files':{},'native3':{k:v.decode('utf-8','replace') for k,v in files.items() if k.endswith(('.js','.json'))}}),text=True,capture_output=True,timeout=30)
    if probe.returncode:raise ValueError('3.x bootstrap graph AST unreadable: '+probe.stderr[-400:])
    graph=json.loads(probe.stdout).get('native3',{})
    if not graph.get('supported'):
        scope=scope or _provider(project,prepared['plan'],prepared['inputs'],'native',files)
        if scope is None:raise ValueError('3.x bootstrap graph needs reviewed resource_package_adapter.v1: provide actual entry closure hashes including settings and engine, startup bundle names; no true-only approval')
        closure=scope.get('bootstrap_inputs');early=scope.get('startup_bundles')
        if not isinstance(closure,dict) or not {'game.js',settings_path}<=set(closure) or not any(k.startswith('cocos-js/') for k in closure):raise ValueError('3.x adapter bootstrap closure must include actual entry/settings/engine bytes')
        if any(sha(files.get(k,b''))!=v for k,v in closure.items()):raise ValueError('3.x adapter bootstrap closure differs from actual artifact')
        if not isinstance(early,list) or not requested<=set(early) or not set(early)<=set(declared)|{'main','internal'}:raise ValueError('3.x adapter startup bundle closure omitted actual preloads or invented a bundle')
        for name in early:
            if name in declared:
                root=declared[name]['root'].rstrip('/')+'/';prehome['subpackages'][root]=sum(len(v) for k,v in files.items() if k.startswith(root))
    prepared['native_boot_graph']=graph



@result_contract
def prepare(project, plan=None, board='localize', *, _read_only=False):
    project=Path(project).resolve();started=time.monotonic()
    with project_lock(project):
        try:
            if not (project/'assets').is_dir():raise ValueError('Cocos assets directory missing')
            version,major=estimate.engine_major(project)
            record=project/HOME/'prepared.json';old=read(record) if record.is_file() else None
            selected=_owner_plan(project,plan,old);fingerprints=tools();current=inputs(project)
            if old and old.get('inputs')==current and old.get('tools')==fingerprints and old.get('requested_plan')==selected and old.get('adapter_identity')==_adapter_identity(project):
                return {**old,'reused':True,'elapsed_seconds':time.monotonic()-started}
            if major=='3':return _prepare3(project,selected,old,fingerprints,current,started,read_only=_read_only)
            if not re.fullmatch(r'2\.4\.\d+',version):return _mapping('engine_resource_adapter',engine=version,required='retain same engine; map actual builder bundle metadata and startup loader before applying',elapsed_seconds=time.monotonic()-started)
            fs=first_screen.analyze(project,'localize');home={x['file'] for x in fs['home_needs']['files']}
            scripts,scan,issues=_scan(project)
            changes,moves,gaps=_move_plan(project,selected,scripts,scan,home);issues+=gaps
            home_scripts={x['file'] for x in fs['home_needs']['files'] if x.get('kind')=='script'}
            for site in scan.get('edits',{}).get('bundle_loads',[]):
                if site['source'] in home_scripts and site['name'] is None and first_screen.runs_before_home(scripts[site['source']],site['start'],fs['boot_scene']!=fs['home_scene']):
                    issues.append(_mapping('dynamic_startup_bundle',source=site['source'],line=site['line'],required='map the finite actual bundle names and startup phase; refresh only this loading dependency'))
            for site in scan.get('sites',[]):
                if site.get('source') not in home_scripts:continue
                offset=int(str(site.get('id','')).rsplit(':',1)[-1]) if str(site.get('id','')).rsplit(':',1)[-1].isdigit() else 0
                if first_screen.runs_before_home(scripts[site['source']],offset,fs['boot_scene']!=fs['home_scene']):
                    for g in selected['deferred_groups']:
                        prefix=g['source'][len('assets/resources/'):]
                        if any(x==prefix or x.startswith(prefix+'/') for x in site.get('paths') or []):
                            issues.append(_mapping('group_requested_before_home',source=site['source'],line=site.get('line'),group=g['source'],required='keep this dependency in startup ownership, or map its actual later loading state; no full test'))
            names=set();dirs=[]
            for item in selected['bundles']:
                directory=relative(item['directory'],assets=True);name=item['name']
                if not re.fullmatch(r'[A-Za-z0-9_.-]+',name) or name.casefold() in names:raise ValueError('duplicate/nonportable bundle name: '+str(name))
                names.add(name.casefold())
                if any(directory==p or directory.startswith(p+'/') or p.startswith(directory+'/') for p in dirs):raise ValueError('overlapping source bundles')
                dirs.append(directory)
                if item.get('independent') is True:issues.append(_mapping('independent_entry',directory=directory,required='independent package needs its own engine/entry; ordinary shared resources are never promoted'))
                if not (project/directory).is_dir() and not any(dst==directory for src,dst in moves):issues.append(_mapping('bundle_directory_missing',directory=directory))
                if item.get('load')=='startup' and name!='resources':issues.append(_mapping('startup_bundle_loading',bundle=name,required='map actual boot load and include whole bundle in first-screen budget'))
                if item.get('load')=='deferred' and not any(g['name']==name for g in selected['deferred_groups']):
                    if not any(re.search(r'loadBundle\s*\(\s*[\'"]'+re.escape(name)+r'[\'"]',s) for s in scripts.values()):issues.append(_mapping('deferred_bundle_callsite',bundle=name))
                # A moved folder's original .meta is copied byte-for-byte first; only bundle fields are changed later.
                actual=next((src for src,dst in moves if dst==directory),directory)
                meta_path,data=_meta(project,actual,name);changes[project/(directory+'.meta')]=data
            boot,gaps=_kit_changes(project,version);changes.update(boot);issues+=gaps
            if issues:return {'schema':SCHEMA,'status':'mapping_required','tasks':issues,'plan':selected,'mutated':False,'elapsed_seconds':time.monotonic()-started}
            if _read_only:
                required=[p.relative_to(project).as_posix() for p,data in changes.items() if (p.read_bytes() if p.is_file() else None)!=data]
                if moves or required:return {'schema':SCHEMA,'status':'needs_prepare','tasks':[_mapping('source_mutation_needed',files=required,moves=[{'from':a,'to':b} for a,b in moves],required='run prepare for these exact resource changes before source finalization')],'mutated':False}
                changes={}
            backup={p:(p.read_bytes() if p.is_file() else None) for p in changes}
            old_outputs={p:(p.read_bytes() if p.is_file() else None) for p in (project.joinpath(*first_screen.OUT),startup_budget.ledger_path(project))}
            applied=[];move_meta={src:(project/(src+'.meta')).read_bytes() for src,dst in moves}
            try:
                for src,dst in moves:
                    (project/dst).parent.mkdir(parents=True,exist_ok=True);shutil.move(str(project/src),str(project/dst));shutil.move(str(project/(src+'.meta')),str(project/(dst+'.meta')));applied.append((src,dst))
                for path,data in changes.items():
                    if data is None:path.unlink(missing_ok=True)
                    else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
                after=fs if _read_only else first_screen.analyze(project,'localize');estimate_report=estimate.audit(project)
                # The verified kit always loads the whole resources bundle before main. FS only sees scene scripts.
                perfile={x['file']:x for x in after['home_needs']['files']+after['deferred']}
                whole_resources=sum(x['bytes'] for x in perfile.values() if x.get('bundle')=='resources')
                early=set(after['groups']['pre_home_bundles'])|({'resources'} if whole_resources else set())
                early_bytes=sum(x['bytes'] for x in perfile.values() if x.get('bundle') in early)
                fs_main=estimate_report['estimate']['main_bytes'];first_bytes=max(after['estimate']['first_download_bytes'],fs_main+early_bytes)
                budget={'main':{'bytes':fs_main,'limit_bytes':MAIN_LIMIT,'basis':'source_estimate','passed':fs_main<=MAIN_LIMIT},
                        'first_download':{'bytes':first_bytes,'limit_bytes':FIRST_LIMIT,'basis':'source_estimate_with_actual_kit_resources_preload','passed':first_bytes<=FIRST_LIMIT},
                        'total':{'bytes':estimate_report['estimate']['total_bytes'],'limit_bytes':estimate.TOTAL_LIMIT}}
                if not _read_only:first_screen.write(project,after)
                ledger=json.loads(json.dumps(after['_ledger'])) if _read_only else startup_budget.load(project)
                for rel,row in perfile.items():
                    if row.get('bundle')=='resources':ledger['files'][rel]={'bytes':row['bytes'],'need':'home' if rel in home else 'deferred','first_download':True,'source':'resource_package_prepare'}
                groups=ledger.setdefault('groups',{});groups['pre_home_bundles']=sorted(set(groups.get('pre_home_bundles',[]))|({'resources'} if whole_resources else set()))
                if not _read_only:startup_budget.save(project,ledger)
                errors=[]
                if not budget['main']['passed']:errors.append(_mapping('main_budget',largest_directories=estimate_report['by_top_folder'],required='map remaining main dependency groups; do not run gameplay/art tests'))
                if not budget['first_download']['passed']:errors.append(_mapping('first_screen_budget',resources_bytes=whole_resources,deferred_groups=[x['file'] for x in after['deferred'] if x.get('bundle')=='resources'],required='map a whole deferred directory and its loading sites, not every image'))
                if budget['total']['bytes']>estimate.TOTAL_LIMIT:errors.append(_mapping('total_budget',required='reduce only identified resource bytes; subpackages do not lower total bytes'))
                result={'schema':SCHEMA,'status':'prepared' if not errors else 'mapping_required','tasks':errors,'plan':selected,'requested_plan':selected,'inputs':inputs(project),'tools':fingerprints,'budget':budget,
                        'first_download_bundles':[_bundle_name(project,b) for b in groups['pre_home_bundles']],'changes':sorted(p.relative_to(project).as_posix() for p in changes if backup[p]!=(p.read_bytes() if p.is_file() else None)),'moves':[{'from':s,'to':d} for s,d in moves],
                        'runtime_boundary':'static dependency/configuration preparation only; first Native must calibrate actual bytes; no gameplay or device pass',
                        'engine':version,'boot_policy':'exact_kit_2.4.15' if version=='2.4.15' else 'preserve_editor_boot_until_actual_native_chain_verified','mutated':not _read_only,'reused':False,'elapsed_seconds':time.monotonic()-started}
                save(record,result);return result
            except BaseException:
                for path,data in {**backup,**old_outputs}.items():
                    if data is None:path.unlink(missing_ok=True)
                    else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
                for src,dst in reversed(applied):
                    if (project/dst).exists():shutil.move(str(project/dst),str(project/src))
                    # Preserve original folder UUID/meta fields on rollback.
                    path=project/(dst+'.meta')
                    if path.exists():path.unlink()
                    (project/(src+'.meta')).write_bytes(move_meta[src])
                raise
        except (ValueError,KeyError,TypeError,OSError,subprocess.SubprocessError) as error:
            return {'schema':SCHEMA,'status':'mapping_required','tasks':[_mapping('resource_input',detail=str(error))],'elapsed_seconds':time.monotonic()-started}


@result_contract
def consume_current(project):
    project=Path(project).resolve();p=project/HOME/'prepared.json'
    if not p.is_file():return _mapping('resource_preparation_missing',required='run resource_package_prepare prepare on current source only')
    old=read(p)
    if old.get('tools')!=tools():return _mapping('resource_rules_changed',required='repeat static resource preparation only')
    if old.get('adapter_identity')!=_adapter_identity(project):return _mapping('resource_adapter_changed',required='review/register the exact adapter and refresh static resource proof only')
    now=inputs(project);changed=sorted(k for k in set(now)|set(old.get('inputs',{})) if now.get(k)!=old['inputs'].get(k))
    if changed:return _mapping('resource_inputs_changed',files=changed,required='assign changed resource groups and refresh static size ledger only')
    return {**old,'reused':True}


def _bundle_name(project,folder):
    p=project/('assets/'+folder+'.meta')
    meta=read(p) if p.is_file() else {}
    return meta.get('bundleName') or (meta.get('userData') or {}).get('bundleName') or folder.rsplit('/',1)[-1]


def _kit_main_versions():
    from tiktok_finalize_steps import load_manifest
    from tiktok_finalize_steps.startup import startup_part
    m=load_manifest();name,_=startup_part(m);return m.all_versions(name)


@result_contract
def calibrate(project,native):
    from upload_size_gate import enforce,json_object
    from package_gates import PackageView
    from package_gates.startup import pre_home_bytes
    project=Path(project).resolve();native=Path(native).resolve();started=time.monotonic()
    with project_lock(project):
        prepared=consume_current(project)
        if prepared.get('status')!='prepared':return prepared
        files={}
        for p in sorted(native.rglob('*')):
            if p.is_symlink():return _mapping('native_resource_symlink',file=p.relative_to(native).as_posix())
            if p.is_file():files[relative(p.relative_to(native).as_posix())]=p.read_bytes()
        binding={k:sha(v) for k,v in files.items()};record=project/HOME/'native-calibration.json'
        old=read(record) if record.is_file() else None
        if old and old.get('source_inputs')==prepared['inputs'] and old.get('native_inputs')==binding and old.get('tools')==prepared['tools']:
            return {**old,'reused':True,'elapsed_seconds':time.monotonic()-started}
        try:
            for name in ('game.js','game.json','project.config.json'):
                if not files.get(name):raise ValueError('missing Native root '+name)
            game=json_object(files['game.json']);sizes=enforce({k:len(v) for k,v in files.items()},game,'tiktok')
            for sub in game.get('subpackages',[]):
                if not files.get(sub['root'].rstrip('/')+'/game.js'):raise ValueError('missing subpackage entry: '+sub['name'])
            view=PackageView(files);prehome=pre_home_bytes(view)
            declared={s['name']:s for s in game.get('subpackages',[])}
            for spec in prepared['plan']['bundles']:
                if spec['name'] not in declared:raise ValueError('planned source bundle absent in Native declarations: '+spec['name'])
                if declared[spec['name']].get('independent') is True:raise ValueError('ordinary source bundle became independent: '+spec['name'])
            if view.engine_major==3:_native3(project,prepared,files,declared,prehome)
            if view.engine_major==2 and 'resources' in declared:
                # Verify the actual entry reaches the resources chain, not a loose filename elsewhere.
                entry=files['game.js'].decode('utf-8','replace')
                main=files.get('main.js',b'').decode('utf-8','replace')
                probe=subprocess.run([first_screen.node_bin(),str(HERE/'resource_package_prepare.cjs')],input=json.dumps({'files':{},'bootstrap':{'entry':entry,'main':main}}),text=True,capture_output=True,timeout=30)
                if probe.returncode:raise ValueError('Native bootstrap AST unreadable: '+probe.stderr[-400:])
                boot=json.loads(probe.stdout)
                if not boot.get('entry_main'):raise ValueError('Native entry needs an actual top-level require of its main.js; map its exact startup anchor')
                known=sha(files.get('main.js',b'')) in _kit_main_versions()
                if not known and not boot.get('editor_resources_chain'):
                    raise ValueError('map same-version editor bootstrap: its real resources loadSubpackage success callback must enter cc.assetManager.loadBundle("resources", originalNext); preserve original startup continuation and retry; no cross-engine template')
            if view.engine_major is None:raise ValueError('cannot identify actual Native engine')
            for name in prepared.get('first_download_bundles',[]):
                if name in declared:
                    root=declared[name]['root'].rstrip('/')+'/'
                    prehome['subpackages'][root]=sum(len(v) for k,v in files.items() if k.startswith(root))
            prehome['total_bytes']=prehome['main_bytes']+sum(prehome['subpackages'].values())
            if prehome['total_bytes']>FIRST_LIMIT:raise ValueError('actual first download %d bytes > %d'%(prehome['total_bytes'],FIRST_LIMIT))
            r={'schema':SCHEMA,'status':'calibrated','source_inputs':prepared['inputs'],'native_inputs':binding,'tools':prepared['tools'],'actual':sizes,'actual_first_download':prehome,
               'estimate':prepared['budget'],'boundary':'Native file accounting and startup static closure, not runtime/device/upload acceptance','reused':False,'elapsed_seconds':time.monotonic()-started}
            save(record,r);return r
        except (ValueError,KeyError,TypeError) as error:return {'schema':SCHEMA,'status':'mapping_required','tasks':[_mapping('native_budget_calibration',detail=str(error))],'elapsed_seconds':time.monotonic()-started}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('prepare','refresh','check','calibrate'));p.add_argument('--project',type=Path,required=True);p.add_argument('--plan',type=Path);p.add_argument('--native',type=Path);p.add_argument('--report',type=Path)
    a=p.parse_args(argv)
    if a.action=='prepare':r=prepare(a.project,read(a.plan) if a.plan else None)
    elif a.action=='refresh':r=refresh_current(a.project)
    elif a.action=='check':r=consume_current(a.project)
    else:
        if not a.native:p.error('calibrate needs --native')
        r=calibrate(a.project,a.native)
    if a.report:save(a.report,r)
    print(json.dumps(r,ensure_ascii=False));return 0 if r.get('status') in ('prepared','calibrated') else 1

if __name__=='__main__':raise SystemExit(main())
