#!/usr/bin/env python3
"""Byte-bound, static Cocos 2 bundle module inputs (never executes package JS).

Only the explicit ``__require = function (...) {...}({id:[factory,deps]},...)``
format is accepted. Module values retain every original byte. The remaining
bytes form a separate envelope, automatically bound to every module consumer.
Unrecognized files have source/error entries but cannot supply module inputs.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
from urllib.parse import quote

SCHEMA = 'bundle-module-inputs.v1'
MODULE_SEP = '::module/'
META_SEP = '::@'
_SOURCES = ContextVar('bundle_module_sources', default=())
_CACHE = ContextVar('bundle_module_cache', default=None)
_NODE = r'''
const fs=require('fs'),crypto=require('crypto'),acorn=require(process.argv[1]);
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
const files=JSON.parse(fs.readFileSync(0,'utf8')),out={};
function walk(n,visit,parent=null){if(!n||typeof n!=='object'||!n.type)return;visit(n,parent);for(const v of Object.values(n)){if(Array.isArray(v))for(const x of v)walk(x,visit,n);else if(v&&v.type)walk(v,visit,n);}}
function key(p){if(p.type!=='Property'||p.computed||p.method||p.kind!=='init')throw Error('non-static property');if(p.key.type==='Identifier')return p.key.name;if(p.key.type==='Literal'&&['string','number'].includes(typeof p.key.value))return String(p.key.value);throw Error('non-static key');}
function req(n){return n?.type==='Identifier'&&n.name==='__require'||n?.type==='MemberExpression'&&(!n.computed&&n.property.name==='__require'||n.computed&&n.property.type==='Literal'&&n.property.value==='__require');}
// Static lexical analysis only. Package code is never evaluated.
function moduleRequests(factory, id, requests) {
 const required = Symbol('factory require');
 const scope = parent => ({parent, bindings:new Map()});
 const resolve = (s,name) => {for(;s;s=s.parent)if(s.bindings.has(name))return s.bindings.get(name);};
 const isRequire = (n,s) => n?.type === 'Identifier' &&
  (resolve(s,n.name) === required || resolve(s,n.name) === undefined && ['require','__require'].includes(n.name));
 function names(p,visit) {
  if(!p)return;
  if(p.type === 'Identifier')visit(p.name);
  else if(p.type === 'RestElement')names(p.argument,visit);
  else if(p.type === 'AssignmentPattern')names(p.left,visit);
  else if(p.type === 'ArrayPattern')for(const x of p.elements)names(x,visit);
  else if(p.type === 'ObjectPattern')for(const x of p.properties)names(x.type === 'RestElement' ? x.argument : x.value,visit);
 }
 function declare(s,p,value=false) {
  names(p,name=>{
   // A var/function redeclaration in the factory cannot shadow its parameter.
   if(s.bindings.get(name) === required)throw Error('escaped module require '+id);
   s.bindings.set(name,value);
  });
 }
 function hoist(n,s) {
  if(!n || !n.type || ['FunctionDeclaration','FunctionExpression','ArrowFunctionExpression','ClassDeclaration','ClassExpression','StaticBlock'].includes(n.type))return;
  if(n.type === 'VariableDeclaration' && n.kind === 'var')for(const d of n.declarations)declare(s,d.id);
  for(const v of Object.values(n)){
   if(Array.isArray(v))for(const x of v)hoist(x,s);
   else if(v?.type)hoist(v,s);
  }
 }
 function lexical(body,s) {
  for(const n of body || []){
   if(n.type === 'VariableDeclaration' && n.kind !== 'var')for(const d of n.declarations)declare(s,d.id);
   else if(['FunctionDeclaration','ClassDeclaration'].includes(n.type) && n.id)declare(s,n.id);
  }
 }
 function pattern(p,s) {
  if(!p)return;
  if(p.type === 'RestElement')pattern(p.argument,s);
  else if(p.type === 'AssignmentPattern'){pattern(p.left,s);visit(p.right,s,p);}
  else if(p.type === 'ArrayPattern')for(const x of p.elements)pattern(x,s);
  else if(p.type === 'ObjectPattern')for(const x of p.properties){
   if(x.type === 'RestElement')pattern(x.argument,s);
   else {if(x.computed)visit(x.key,s,x);pattern(x.value,s);}
  }
 }
 function fn(n,parent,root=false) {
  const s=scope(parent);
  if(n.id)declare(s,n.id);
  for(const p of n.params)declare(s,p);
  if(root && n.params[0])s.bindings.set(n.params[0].name,required);
  // Parameter defaults use the parameter environment, before body var bindings.
  for(const p of n.params)pattern(p,s);
  hoist(n.body,s);
  if(n.body.type === 'BlockStatement'){
   lexical(n.body.body,s);
   for(const x of n.body.body)visit(x,s,n.body);
  }else visit(n.body,s,n);
 }
 function visit(n,s,parent=null) {
  if(!n || !n.type)return;
  if(['FunctionDeclaration','FunctionExpression','ArrowFunctionExpression'].includes(n.type)){fn(n,s);return;}
  if(n.type === 'BlockStatement' || n.type === 'StaticBlock'){
   const child=scope(s);if(n.type === 'StaticBlock')hoist({type:'BlockStatement',body:n.body},child);
   lexical(n.body,child);for(const x of n.body)visit(x,child,n);return;
  }
  if(n.type === 'CatchClause'){
   const child=scope(s);declare(child,n.param);pattern(n.param,child);visit(n.body,child,n);return;
  }
  if(['ForStatement','ForInStatement','ForOfStatement'].includes(n.type)){
   const child=scope(s),d=n.init || n.left;
   if(d?.type === 'VariableDeclaration' && d.kind !== 'var')for(const x of d.declarations)declare(child,x.id);
   for(const field of ['init','left','right','test','update','body'])visit(n[field],child,n);return;
  }
  if(n.type === 'SwitchStatement'){
   visit(n.discriminant,s,n);const child=scope(s);
   lexical(n.cases.flatMap(c=>c.consequent),child);
   for(const c of n.cases)visit(c,child,n);return;
  }
  if(n.type === 'ClassDeclaration' || n.type === 'ClassExpression'){
   const child=scope(s);if(n.id)declare(child,n.id);
   visit(n.superClass,child,n);visit(n.body,child,n);return;
  }
  if(n.type === 'VariableDeclarator'){pattern(n.id,s);visit(n.init,s,n);return;}
  if(n.type === 'Identifier'){
   const propertyName=parent?.type === 'MemberExpression' && !parent.computed && parent.property === n ||
    ['Property','MethodDefinition','PropertyDefinition'].includes(parent?.type) && !parent.computed && parent.key === n && !parent.shorthand ||
    ['LabeledStatement','BreakStatement','ContinueStatement'].includes(parent?.type) && parent.label === n;
   const directCall=parent?.type === 'CallExpression' && parent.callee === n;
   const typeObservation=parent?.type === 'UnaryExpression' && parent.operator === 'typeof' && parent.argument === n;
   if(!propertyName && isRequire(n,s) && !directCall && !typeObservation)throw Error('escaped module require '+id);
  }
  // Keep the existing conservative dynamic-evaluation refusal unchanged.
  if((n.type === 'CallExpression' || n.type === 'NewExpression') && n.callee.type === 'Identifier' && ['eval','Function'].includes(n.callee.name))throw Error('dynamic factory evaluation '+id);
  if(n.type === 'CallExpression' && (isRequire(n.callee,s) || n.callee.type === 'MemberExpression' && req(n.callee))){
   const a=n.arguments[0];
   if(n.arguments.length !== 1 || a?.type !== 'Literal' || !['string','number'].includes(typeof a.value))throw Error('dynamic module require '+id);
   requests.push(String(a.value));
  }
  for(const v of Object.values(n)){
   if(Array.isArray(v))for(const x of v)visit(x,s,n);
   else if(v?.type)visit(v,s,n);
  }
 }
 fn(factory,null,true);
}

for(const [path,source] of Object.entries(files)){
 try{
  let ast;try{ast=acorn.parse(source,{ecmaVersion:'latest',sourceType:'script',allowHashBang:true});}catch(_){ast=acorn.parse(source,{ecmaVersion:'latest',sourceType:'module',allowHashBang:true});}
  const candidates=[];walk(ast,n=>{if(n.type==='AssignmentExpression'&&req(n.left))candidates.push(n.right);if(n.type==='VariableDeclarator'&&req(n.id))candidates.push(n.init);});
  if(candidates.length!==1){let system=false;walk(ast,n=>{if(n.type==='CallExpression'&&n.callee.type==='MemberExpression'&&n.callee.object.type==='Identifier'&&n.callee.object.name==='System'&&n.callee.property.name==='register')system=true;});throw Error(system?'unsupported Cocos 3 System.register format; module adapter required':'expected one static Cocos 2 __require assignment');}
  const call=candidates[0];if(call?.type!=='CallExpression'||call.callee.type!=='FunctionExpression'||call.arguments[0]?.type!=='ObjectExpression')throw Error('unsupported __require call format');
  const table=call.arguments[0],mods=new Map(),ranges=[];
  for(const property of table.properties){
   const id=key(property),value=property.value;if(id==='__proto__')throw Error('prototype module key is unsupported');
   if(mods.has(id)||value.type!=='ArrayExpression'||value.elements.length!==2||value.elements[0]?.type!=='FunctionExpression'||value.elements[1]?.type!=='ObjectExpression')throw Error('unsupported/duplicate module '+id);
   const factory=value.elements[0],depmap=value.elements[1],deps=new Map(),requests=[];
   for(const dep of depmap.properties){const name=key(dep),v=dep.value;if(deps.has(name))throw Error('duplicate dependency '+name);if(v.type==='Literal'&&['string','number'].includes(typeof v.value))deps.set(name,String(v.value));else if(v.type==='UnaryExpression'&&v.operator==='void'&&v.argument.type==='Literal'&&v.argument.value===0)deps.set(name,name);else throw Error('unsupported dependency '+name);}
   const param=factory.params[0];if(factory.params.length>3||factory.params.some(p=>p.type!=='Identifier'))throw Error('non-static factory parameters');
   moduleRequests(factory,id,requests);
   function checkArgs(n,depth=0){if(!n||typeof n!=='object'||!n.type)return;if(n.type==='Identifier'&&n.name==='arguments'&&depth===0)throw Error('factory arguments access '+id);const next=depth+(['FunctionExpression','FunctionDeclaration'].includes(n.type)?1:0);for(const v of Object.values(n)){if(Array.isArray(v))for(const x of v)checkArgs(x,next);else if(v&&v.type)checkArgs(v,next);}}checkArgs(factory.body);
   mods.set(id,{own:hash(source.slice(value.start,value.end)),deps,requests});ranges.push([value.start,value.end]);
  }
  if(!mods.size)throw Error('empty module table');
  // Entry module order/cache and every wrapper byte stay in the envelope.
  const envelope=[];let offset=0;for(const [start,end] of ranges.sort((a,b)=>a[0]-b[0])){envelope.push(source.slice(offset,start));offset=end;}envelope.push(source.slice(offset));
  const rows={};
  for(const [id] of mods){const seen=new Set();function include(k){if(!mods.has(k))k=k.split('/').pop();if(!mods.has(k))throw Error('unresolved external module '+k+' from '+id);if(seen.has(k))return;seen.add(k);const m=mods.get(k);for(const request of [...m.deps.keys(),...m.requests])include(m.deps.get(request)??request);}include(id);const closure=[...seen].sort().map(k=>[k,mods.get(k).own]);rows[id]=hash(JSON.stringify({own:mods.get(id).own,closure}));}
  out[path]={format:'cocos2-require-table.v1',source:hash(source),envelope:hash(JSON.stringify(envelope)),modules:rows};
 }catch(e){out[path]={source:hash(source),error:String(e.message||e)};}
}
process.stdout.write(JSON.stringify(out));
'''


class ModuleInputError(ValueError):
    pass


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def module_key(bundle, module_id):
    return bundle + MODULE_SEP + quote(str(module_id), safe='')


def module_bundle(key):
    return key.split(MODULE_SEP, 1)[0] if MODULE_SEP in key else None


def _files(source):
    if isinstance(source, (str, Path)):
        root = Path(source).resolve()
        if not root.is_dir():
            raise ModuleInputError('模块字节来源必须是实际包目录或 files dict')
        return {p.relative_to(root).as_posix(): p.read_bytes()
                for p in sorted(root.rglob('*.js')) if p.is_file()}
    if not isinstance(source, dict):
        raise ModuleInputError('模块字节来源必须是实际包目录或 files dict')
    result = {}
    for path, raw in source.items():
        if (not isinstance(path, str) or path.startswith('/') or '..' in PurePosixPath(path).parts
                or MODULE_SEP in path or META_SEP in path):
            raise ModuleInputError('模块来源含无效相对路径：' + repr(path))
        if path.endswith('.js'):
            if isinstance(raw, Path):
                raw = raw.read_bytes()
            if not isinstance(raw, bytes):
                raise ModuleInputError('模块来源必须提供原始 bytes：' + path)
            result[path] = raw
    return result


@contextmanager
def module_sources(current_files, baseline_files=None):
    """Register actual bytes lazily; old ledger rows may match the baseline.

    No package files are read or parsed unless a modules scope requests them.
    Sources never change stored ledger records or their original identities.
    """
    sources = []
    for source in (current_files, baseline_files, *_SOURCES.get()):
        if source is not None and not any(source is prior for prior in sources):
            sources.append(source)
    token = _SOURCES.set(tuple(sources))
    cache_token = _CACHE.set(dict(_CACHE.get() or {}))
    try:
        yield
    finally:
        _SOURCES.reset(token)
        _CACHE.reset(cache_token)


def expand_module_roots(roots, source_files):
    """Add a static manifest after matching every package JS byte to its hash."""
    package = roots.get('package')
    if not isinstance(package, dict):
        raise ModuleInputError('模块依赖需要 package 原始字节清单')
    supplied = _files(source_files)
    scripts = {p: digest for p, digest in package.items() if p.endswith('.js')}
    for path, expected in scripts.items():
        if path not in supplied or _sha(supplied[path]) != expected:
            raise ModuleInputError('模块来源与 package SHA-256 不符或原字节缺失：' + path)
    texts = {}
    for path in scripts:
        try:
            texts[path] = supplied[path].decode('utf-8')
        except UnicodeError as exc:
            raise ModuleInputError('模块脚本不是严格 UTF-8：' + path) from exc
    try:
        proc = subprocess.run(['node', '-e', _NODE, str(Path(__file__).with_name('vendor')/'acorn.cjs')],
                              input=json.dumps(texts, ensure_ascii=False), capture_output=True,
                              text=True, check=True, timeout=45)
        parsed = json.loads(proc.stdout)
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        raise ModuleInputError('静态模块解析失败：' + str(exc)) from exc
    values = {}
    parser_digest = _sha((Path(__file__).with_name('vendor')/'acorn.cjs').read_bytes())
    for path, row in parsed.items():
        if row.get('source') != scripts[path]:
            raise ModuleInputError('静态解析未绑定原始包字节：' + path)
        values[path + META_SEP + 'source'] = row['source']
        if 'error' in row:
            values[path + META_SEP + 'error'] = row['error']
            continue
        values[path + META_SEP + 'format'] = row['format']
        values[path + META_SEP + 'parser'] = parser_digest
        values[path + META_SEP + 'envelope'] = row['envelope']
        for module_id, digest in row['modules'].items():
            values[module_key(path, module_id)] = digest
    return dict(roots, modules=values)


def with_module_inputs(roots, source_files=None, *, scope=None):
    """Only expand explicit module scopes; unrelated/legacy runners are unchanged."""
    if scope is None or 'modules' not in scope.get('inputs', {}):
        return roots
    sources = (source_files,) if source_files is not None else _SOURCES.get()
    if not sources:
        raise ModuleInputError('modules 依赖缺少实际包字节来源，不能凭 basis 沿用')
    cache = _CACHE.get() if source_files is None else None
    identity = tuple(sorted((p, v) for p, v in roots.get('package', {}).items() if p.endswith('.js')))
    if cache is not None and identity in cache:
        return dict(roots, modules=cache[identity])
    errors = []
    for source in sources:
        try:
            expanded = expand_module_roots(roots, source)
            if cache is not None:
                cache[identity] = expanded['modules']
            return expanded
        except ModuleInputError as exc:
            errors.append(str(exc))
    # A repaired candidate may follow several real intermediate executions, not
    # just the last delivered ZIP. Recover their original JS by content hash;
    # never trust a stored module decomposition without its original bytes.
    archive = os.environ.get('ENGLISH_CHECK_MODULE_ARCHIVE')
    if archive:
        folder = Path(archive).resolve()
        recovered = {}
        for path, expected in roots.get('package', {}).items():
            if path.endswith('.js'):
                item = folder / (expected + '.js')
                if item.is_file():
                    raw = item.read_bytes()
                    if _sha(raw) != expected:
                        raise ModuleInputError('历史模块原始字节校验失败：' + path)
                    recovered[path] = raw
        try:
            expanded = expand_module_roots(roots, recovered)
            if cache is not None:
                cache[identity] = expanded['modules']
            return expanded
        except ModuleInputError as exc:
            errors.append(str(exc))
    raise ModuleInputError('；'.join(errors))


def module_coverage(old_roots, new_roots):
    """Report whether changed package JS has complete old/new byte decompositions.

    ``covered`` is deliberately false for envelope changes: a gate must not
    replace a changed bundle with a narrow module-only scope in that case.
    """
    a, b = old_roots.get('package', {}), new_roots.get('package', {})
    changed = sorted(p for p in set(a) | set(b) if p.endswith('.js') and a.get(p) != b.get(p))
    before, after = old_roots.get('modules', {}), new_roots.get('modules', {})
    bad, envelope, errors = [], [], []
    for path in changed:
        for label, package, modules in (('old', a, before), ('new', b, after)):
            if (path not in package or modules.get(path + META_SEP + 'source') != package.get(path)
                    or modules.get(path + META_SEP + 'format') != 'cocos2-require-table.v1'
                    or not modules.get(path + META_SEP + 'envelope')
                    or not any(k.startswith(path + MODULE_SEP) for k in modules)):
                bad.append(path)
                errors.append(label + ':' + path + ':' + str(modules.get(path + META_SEP + 'error', 'missing verified module decomposition')))
        if before.get(path + META_SEP + 'envelope') != after.get(path + META_SEP + 'envelope'):
            envelope.append(path)
    changed_modules = sorted(k for k in set(before) | set(after)
                             if MODULE_SEP in k and before.get(k) != after.get(k))
    return {'schema': SCHEMA, 'covered': not bad and not envelope,
            'changed_bundles': changed, 'changed_modules': changed_modules,
            'envelope_changed': sorted(set(envelope)), 'unparsed_bundles': sorted(set(bad)), 'errors': errors}
