#!/usr/bin/env python3
"""Refuse missing literal packaged paths, atlas bounds and stale texture fingerprints.
Does not infer dynamic paths or prove engine/SDK runtime readiness.
"""
from pathlib import Path, PurePosixPath
import argparse,hashlib,json,re,struct
LITERAL=re.compile(r'''["']((?:preview-ui|subpackages|assets|src|cocos)/[^"'\n]+\.(?:png|jpg|jpeg|json|js|mp3))["']''')

def _reject_duplicate_json_keys(pairs):
 out={}
 for key,value in pairs:
  if key in out:raise ValueError('duplicate JSON key: '+key)
  out[key]=value
 return out

def _safe_relative(root, rel):
 if not isinstance(rel,str) or not rel or '\\' in rel or '\x00' in rel:return None
 posix=PurePosixPath(rel)
 if posix.is_absolute() or posix.as_posix()!=rel or any(part in ('','..','.') for part in rel.split('/')):return None
 candidate=root.joinpath(*posix.parts)
 try:
  if not candidate.resolve(strict=False).is_relative_to(root.resolve()):return None
 except (OSError,RuntimeError):return None
 return candidate

def _is_ant_v6(root):
 if (root/'ant-content-manifest.js').exists() or (root/'ant-content.js').exists():return True
 game=root/'game.js'
 if game.is_file():
  try:
   if 'ant-content-manifest.js' in game.read_text(errors='replace') or 'ant-content.js' in game.read_text(errors='replace'):return True
  except OSError:pass
 return False

def _ant_v6_manifest(root, errors):
 manifest_path=root/'ant-content-manifest.js';content_path=root/'ant-content.js'
 if not manifest_path.is_file():errors.append('Ant v6 manifest missing: ant-content-manifest.js');return None
 if not content_path.is_file():errors.append('Ant v6 resolver missing: ant-content.js');return None
 try:
  raw=manifest_path.read_text(encoding='utf-8')
  prefix='module.exports='
  if not raw.startswith(prefix) or not raw.rstrip().endswith(';'):
   raise ValueError('manifest must be a pure JSON module.exports assignment')
  body=raw[len(prefix):].rstrip()
  body=body[:-1]
  doc=json.loads(body,object_pairs_hook=_reject_duplicate_json_keys)
 except (OSError,UnicodeError,ValueError,json.JSONDecodeError) as exc:
  errors.append('Ant v6 manifest invalid: '+str(exc));return None
 if not isinstance(doc,dict) or doc.get('version')!=6:
  errors.append('Ant v6 manifest version must be 6');return None
 mapping=doc.get('mapping');groups=doc.get('groups')
 if not isinstance(mapping,dict) or not isinstance(groups,dict):
  errors.append('Ant v6 manifest requires mapping and groups objects');return None
 game_path=root/'game.json'
 try:
  game=json.loads(game_path.read_text(encoding='utf-8'),object_pairs_hook=_reject_duplicate_json_keys)
 except (OSError,UnicodeError,ValueError,json.JSONDecodeError) as exc:
  errors.append('Ant v6 game.json invalid: '+str(exc));return None
 declared={}
 subpackages=game.get('subpackages') if isinstance(game,dict) else None
 if not isinstance(subpackages,list):
  errors.append('Ant v6 game.json has no subpackages list');return None
 for item in subpackages:
  if not isinstance(item,dict) or not isinstance(item.get('name'),str) or not isinstance(item.get('root'),str):
   errors.append('Ant v6 game.json has malformed subpackage declaration');continue
  name=item['name']
  if name in declared:errors.append('duplicate Ant v6 subpackage declaration: '+name)
  declared[name]=item['root']
 resolved={};group_sources={};target_owners={}
 hash_re=re.compile(r'^[0-9a-f]{64}$')
 for source,entry in mapping.items():
  if _safe_relative(root,source) is None or not source.startswith('subpackages/resources/'):
   errors.append('unsafe or non-resource Ant v6 mapping source: '+str(source));continue
  if not isinstance(entry,dict) or not {'path','group','sha256','bytes'}.issubset(entry) or set(entry)-{'path','group','sha256','bytes','output_sha256','output_bytes'}:
   errors.append('Ant v6 mapping entry has invalid fields: '+source);continue
  target=entry.get('path');group=entry.get('group');input_sha=entry.get('sha256');input_bytes=entry.get('bytes')
  if _safe_relative(root,target) is None:
   errors.append('unsafe Ant v6 mapping target: '+str(target)+' from '+source);continue
  if not isinstance(input_sha,str) or not hash_re.fullmatch(input_sha) or not isinstance(input_bytes,int) or isinstance(input_bytes,bool) or input_bytes<0:
   errors.append('invalid Ant v6 source SHA/bytes: '+source);continue
  output_sha=entry.get('output_sha256',input_sha);output_bytes=entry.get('output_bytes',input_bytes)
  if ('output_sha256' in entry)!=('output_bytes' in entry) or not isinstance(output_sha,str) or not hash_re.fullmatch(output_sha) or not isinstance(output_bytes,int) or isinstance(output_bytes,bool) or output_bytes<0:
   errors.append('invalid Ant v6 output SHA/bytes: '+source);continue
  if group is None:name='resources'
  elif isinstance(group,str) and group:name=group
  else:errors.append('invalid Ant v6 group: '+source);continue
  expected_root='subpackages/'+name
  if declared.get(name)!=expected_root:
   errors.append('Ant v6 group/root is not declared exactly: '+str(group)+' -> '+str(declared.get(name))+' from '+source);continue
  if not target.startswith(expected_root+'/'):
   errors.append('Ant v6 target is outside its declared group root: '+target+' for '+str(group));continue
  if target in target_owners:
   errors.append('duplicate Ant v6 target mapping: '+target+' from '+target_owners[target]+' and '+source);continue
  target_owners[target]=source
  candidate=_safe_relative(root,target)
  if candidate is None or not candidate.is_file():
   errors.append('Ant v6 mapped target missing: '+target+' from '+source);continue
  data=candidate.read_bytes();actual_sha=hashlib.sha256(data).hexdigest()
  if len(data)!=output_bytes:errors.append('Ant v6 mapped target byte count mismatch: '+target)
  if actual_sha!=output_sha:errors.append('Ant v6 mapped target SHA-256 mismatch: '+target)
  resolved[source]=target
  if group is not None:group_sources.setdefault(group,[]).append(source)
 for group,entry in groups.items():
  if not isinstance(group,str) or not group or not isinstance(entry,dict) or set(entry)!={'bytes','files'}:
   errors.append('invalid Ant v6 group manifest entry: '+str(group));continue
  files=entry.get('files');declared_bytes=entry.get('bytes')
  if not isinstance(files,list) or any(not isinstance(x,str) for x in files) or len(set(files))!=len(files):
   errors.append('invalid Ant v6 group file list: '+group);continue
  expected=sorted(group_sources.get(group,[]))
  if sorted(files)!=expected:errors.append('Ant v6 group file mapping mismatch: '+group)
  if not isinstance(declared_bytes,int) or isinstance(declared_bytes,bool) or declared_bytes<0:
   errors.append('invalid Ant v6 group byte total: '+group);continue
  actual_bytes=0
  for source in expected:
   entry=mapping.get(source,{})
   actual_bytes+=entry.get('output_bytes',entry.get('bytes',0))
  if actual_bytes!=declared_bytes:errors.append('Ant v6 group byte total mismatch: '+group)
 if set(groups)!=set(group_sources):errors.append('Ant v6 groups do not exactly cover mapped non-resource groups')
 for name,root_name in declared.items():
  if name=='resources' or name.startswith('ant_'):
   if root_name!='subpackages/'+name:errors.append('Ant v6 subpackage root mismatch: '+name)
 startup=doc.get('startup_subpackages')
 if not isinstance(startup,list) or any(not isinstance(x,str) or x not in declared for x in startup):
  errors.append('Ant v6 startup_subpackages contains undeclared names')
 return {'mapping':mapping,'resolved':resolved,'targets':set(target_owners),'groups':groups,'valid':not errors}

def _cocos24_texture_pack_refs(root, errors, resolved=None):
 """Resolve native extensions from actual Cocos 2.4 Texture2D pack metadata."""
 alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
 def uuid(value):
  value=value.split('@',1)[0]
  if len(value)==22:
   digits=value[:2]
   for i in range(2,22,2):digits+=format((alphabet.index(value[i])<<6)|alphabet.index(value[i+1]),'03x')
   return '-'.join([digits[:8],digits[8:12],digits[12:16],digits[16:20],digits[20:]])
  return value
 refs=[]
 for config in root.rglob('config.json'):
  if not any(part in {'assets','subpackages'}for part in config.relative_to(root).parts):continue
  try:c=json.loads(config.read_text())
  except (ValueError,OSError):continue
  if not isinstance(c,dict) or not isinstance(c.get('packs'),dict) or not isinstance(c.get('uuids'),list):continue
  base=config.parent
  for pack,indices in c['packs'].items():
   if not isinstance(indices,list):continue
   p=base/c.get('importBase','import')/pack[:2]/(pack+'.json')
   if not p.is_file():continue  # Other pack/version protocols retain their existing loader checks.
   try:data=json.loads(p.read_text())
   except (ValueError,OSError):continue
   if not isinstance(data,dict) or data.get('type')!='cc.Texture2D' or not isinstance(data.get('data'),str):continue
   entries=data['data'].split('|')
   if len(entries)!=len(indices):errors.append('Cocos Texture2D pack length mismatch: '+str(p.relative_to(root)));continue
   versions=c.get('versions',{}).get('native',[]) if isinstance(c.get('versions',{}),dict) else []
   native_versions={versions[i]:versions[i+1]for i in range(0,len(versions)-1,2)}
   for index,entry in zip(indices,entries):
    if type(index) is int and 0<=index<len(c['uuids']):encoded_uuid=c['uuids'][index]
    elif isinstance(index,str) and index in c['uuids']:encoded_uuid=index
    else:errors.append('Cocos Texture2D pack UUID index invalid: '+str(p.relative_to(root)));continue
    ext_field=entry.split(',',1)[0]
    if not ext_field:continue  # Render textures do not have a native file.
    try:identifier=uuid(encoded_uuid)
    except (ValueError,TypeError,AttributeError):errors.append('Cocos texture UUID invalid: '+str(p.relative_to(root)));continue
    for token in ext_field.split('_'):
     ext=token.split('@',1)[0];formats=['.png','.jpg','.jpeg','.bmp','.webp','.pvr','.pkm','.astc']
     if ext.isdigit() and int(ext)<len(formats):ext=formats[int(ext)]
     if not ext.startswith('.') or '/' in ext or '\\' in ext:errors.append('Cocos texture extension invalid: '+str(p.relative_to(root)));continue
     version=native_versions.get(index,'');name=identifier+('.'+version if version else '')+ext
     target=(base/c.get('nativeBase','native')/identifier[:2]/name).resolve()
     try:rel=target.relative_to(root.resolve()).as_posix()
     except ValueError:errors.append('Cocos native texture escapes package: '+str(target));continue
     row={'pack':str(p.relative_to(root)),'uuid_index':index,'path':rel}
     # Ant v6 keeps serialized UUID references while its validated manifest
     # resolves exact bytes under declared normal-subpackage roots.
     mapped=(resolved or {}).get(rel)
     if mapped is not None:
      target=root/mapped;row['resolved_path']=mapped
     refs.append(row)
     if not target.is_file():errors.append('missing Cocos packed native texture: '+rel+' from '+str(p.relative_to(root)))
 return refs


# A resolver is trusted as reviewed executable bytes, never by a label or regex.
# This profile is limited to one Cocos 2.4 pre-download audio-subpackage adapter.
# Other adapters/entry variants retain the original literal-file requirement.
_AUDIO_RESOLVERS = {
 '9e5101b9f2b932b41c013238552e2d8369734b4ab9c79ad6f3b6e6ff9e2ba941': {
  'source_path':'adapter.js',
  'entry_sha256':'d94cae52074606c8add51be798a3b826a7ad9a48df22537260a35314c62de20a',
  'bundle':'audio','bundle_root':'subpackages/audio',
 },
}

def _reviewed_audio_aliases(root, path, source_bytes, errors):
 profile=_AUDIO_RESOLVERS.get(hashlib.sha256(source_bytes).hexdigest())
 if profile is None or path.relative_to(root).as_posix()!=profile['source_path']:return {}
 try:
  entry=root/'game.js'
  if not entry.is_file() or hashlib.sha256(entry.read_bytes()).hexdigest()!=profile['entry_sha256']:
   raise ValueError('reviewed audio resolver entry fingerprint mismatch')
  source=source_bytes.decode('utf-8')
  matches=re.findall(r'var AUDIO_BUNDLE_MAP = (\{[^\n]+\});',source)
  if len(matches)!=1:raise ValueError('reviewed audio resolver mapping missing or ambiguous')
  aliases=json.loads(matches[0],object_pairs_hook=_reject_duplicate_json_keys)
  if not isinstance(aliases,dict) or not aliases or not all(isinstance(k,str) and isinstance(v,str) for k,v in aliases.items()):
   raise ValueError('invalid reviewed audio resolver mapping')
  config=json.loads((root/'game.json').read_text(),object_pairs_hook=_reject_duplicate_json_keys)
  subpackages=config.get('subpackages',config.get('subPackages',[]))
  if not isinstance(subpackages,list):raise ValueError('reviewed audio resolver subpackages must be a list')
  declared=[item for item in subpackages if isinstance(item,dict) and item.get('name')==profile['bundle']]
  if len(declared)!=1 or not isinstance(declared[0].get('root'),str) or declared[0]['root'].rstrip('/')!=profile['bundle_root']:
   raise ValueError('reviewed audio resolver subpackage declaration mismatch')
  for original,target in aliases.items():
   resolved=_safe_relative(root,target)
   if (_safe_relative(root,original) is None or resolved is None or not original.endswith('.mp3') or
       not target.startswith(profile['bundle_root']+'/native/') or
       original.split('/native/',1)[-1]!=target.split('/native/',1)[-1]):
    raise ValueError('unsafe or mismatched reviewed audio resolver target: '+target)
   if not resolved.is_file():raise ValueError('reviewed audio resolver target missing: '+target)
  # Follow actual package requires, including the adapter and subpackage entry.
  # This uses the existing byte/tool-fingerprinted pure parse cache when a
  # writer already checked startup; it never executes a project runner.
  from audit_upload_startup import audit_files
  files={p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
  startup=audit_files(files)
  if not startup['passed']:raise ValueError('reviewed audio resolver startup closure: '+'; '.join(startup['errors']))
  return aliases
 except (OSError,ValueError,TypeError,AttributeError,KeyError) as exc:
  errors.append(str(exc))
  return {}


def audit(root):
 root=Path(root);errors=[];refs=[];atlases=0
 ant_mode=_is_ant_v6(root)
 ant_manifest=_ant_v6_manifest(root,errors) if ant_mode else None
 resolver=ant_manifest['resolved'] if ant_manifest is not None and ant_manifest.get('valid') else None
 native_texture_refs=_cocos24_texture_pack_refs(root,errors,resolver)
 for p in root.rglob('*.js'):
  source_bytes=p.read_bytes();source=source_bytes.decode('utf-8',errors='replace')
  audio_aliases=_reviewed_audio_aliases(root,p,source_bytes,errors)
  for m in LITERAL.finditer(source):
   rel=m.group(1)
   if any(c in rel for c in ['+','{','}']):continue
   refs.append({'source':str(p.relative_to(root)),'path':rel})
   # Cocos 2 settings.js resolves jsList from src/; other packaged literals
   # continue to resolve from the package root.
   if ant_mode:
    candidate=_safe_relative(root,rel)
    if candidate is None:
     errors.append('unsafe Ant v6 literal path: '+rel+' from '+str(p.relative_to(root)));continue
    if ant_manifest is not None:
     mapped=ant_manifest['resolved'].get(rel)
     if mapped is not None:candidate=root/mapped
    if p.relative_to(root).as_posix()=='src/settings.js' and rel.startswith('assets/'):
     candidate=root/'src'/rel
   else:
    candidate=root/rel
    if p.relative_to(root).as_posix()=='src/settings.js' and rel.startswith('assets/'):
     candidate=root/'src'/rel
   if rel in audio_aliases:
    resolved=_safe_relative(root,audio_aliases[rel])
    if resolved is None:errors.append('unsafe audio alias target: '+audio_aliases[rel]);continue
    candidate=resolved;refs[-1]['resolved_path']=audio_aliases[rel]
   if not candidate.is_file():errors.append('missing packaged asset: '+rel+' from '+str(p.relative_to(root)))
 for p in [root/'game.js',root/'ccRequire.js']:
  if not p.is_file():continue
  for name in re.findall(r'''require\(\s*["']([^"']+)["']\s*\)''',p.read_text()):
   candidate=root/name
   if not candidate.is_file() and not candidate.with_suffix('.js').is_file():errors.append('missing entry require: '+name)
 for p in root.rglob('frames.json'):
  try:
   manifest=json.loads(p.read_text());textures=manifest.get('textures',{})
   if not textures:continue
   atlases+=1
   for key,v in textures.items():
    tex=p.parent/(key+'.png')
    if not tex.is_file():errors.append('atlas texture missing: '+str(tex));continue
    data=tex.read_bytes()
    if data[:8]!=b'\x89PNG\r\n\x1a\n':errors.append('not PNG: '+str(tex));continue
    w,h=struct.unpack('>II',data[16:24])
    if (w,h)!=(v.get('width'),v.get('height')):errors.append('atlas texture dimensions: '+key)
    if hashlib.sha256(data).hexdigest()!=v.get('sha256'):errors.append('atlas texture fingerprint: '+key)
   for name,v in manifest.get('frames',{}).items():
    tex=textures.get(v.get('texture'),{});x,y,w,h=v.get('rect',[-1]*4)
    if min(x,y)<0 or min(w,h)<=0 or x+w>tex.get('width',0) or y+h>tex.get('height',0):errors.append('atlas frame out of bounds: '+name)
  except (ValueError,OSError,TypeError,KeyError) as e:errors.append('atlas manifest unreadable: '+str(p)+': '+str(e))
 return {'tool':'audit_packed_assets','passed':not errors,'errors':sorted(set(errors)),'literal_references':refs,'native_texture_references':native_texture_refs,'atlases':atlases,'boundary':'static packaged references and texture metadata only'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--out',type=Path);a=p.parse_args();r=audit(a.root)
 if a.out:a.out.write_text(json.dumps(r,indent=2))
 print(json.dumps(r));raise SystemExit(not r['passed'])
