from pathlib import Path
# P20 (问题普查 T20): without Pillow this script ended in a Traceback, even for --help. The shared guard in
# cocos-game-check/package-check/scripts/check_guard.py turns that into a "not_run" line (exit 2) and keeps --help.
if __name__ == '__main__':
    import importlib.util as _ilu
    _cg = Path(__file__).resolve().parents[2] / 'cocos-game-check' / 'package-check' / 'scripts' / 'check_guard.py'
    if _cg.is_file():
        _spec = _ilu.spec_from_file_location('check_guard', _cg)
        _mod = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        _mod.need_modules('PIL')
from PIL import Image
import re

def components(image,threshold=64):
 a=image.convert('RGBA').getchannel('A');w,h=a.size;data=a.point(lambda x:255 if x>threshold else 0).tobytes();parent=[];segments=[];previous=[]
 def root(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 for y in range(h):
  current=[]
  for m in re.finditer(b'\xff+',data[y*w:(y+1)*w]):
   x0,x1=m.span();links=[root(k) for a,b,k in previous if b>=x0 and a<=x1]
   k=min(links) if links else len(parent)
   if not links:parent.append(k)
   else:
    for other in links:parent[root(other)]=root(k)
   current.append((x0,x1,k));segments.append((x0,x1,y,k))
  previous=current
 stats={}
 for x0,x1,y,k in segments:
  k=root(k)
  if k not in stats:stats[k]={'id':k,'area':0,'bbox':[x0,y,x1,y+1],'runs':[]}
  d=stats[k];d['area']+=x1-x0;b=d['bbox'];b[0]=min(b[0],x0);b[1]=min(b[1],y);b[2]=max(b[2],x1);b[3]=max(b[3],y+1);d['runs'].append((x0,x1,y))
 return stats

def inside(component,rect):
 x,y,w,h=rect;return sum(max(0,min(x1,x+w)-max(x0,x)) for x0,x1,yy in component['runs'] if y<=yy<y+h)

import argparse,json,hashlib,sys
from PIL import ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parent))
import plist_atlas_adapter as plist

# v7.8 (总表 H9（补）, Ingrid's Snowball Stack 10-26: three rounds of slice residue on caption_*, closet, snowball): every
# other slice is checked too - picture text, game pieces, projectiles, obstacles. Role "scope_body": the main body must
# not be cut by the rect and no thin alpha strip may hang on the rect edge (a neighbour's sliver). Detached own parts
# (letters, sparkles) are allowed. Tilesets / seamless tiles / sliced plates are skipped: they are meant to join.
TILE_NAME=re.compile(r'tile|tileset|terrain|ground|floor|wall|road|grass|water|map|bg|background|backdrop|pattern|seamless|loop|strip|border|frame9|9slice|sliced|nine|bar|fill|line',re.I)
# art patch v3 (2026-10-31): 'panel' is not a tile name (PaperCutKid panel_reward / panel_settings: gift, lightning, gear and star ornaments
# cut at the top); real 9-slice / tiled plates are still skipped by sliced / tiled and opaque_edges.
# Sheet splitters (Aseprite, TexturePacker "split sheet") name animation cells tile000, tile001...: those are bodies.
AUTO_TILE=re.compile(r'tile\d+',re.I)
def _flat_any(data):
 return isinstance(data,dict) and bool(data) and all(isinstance(v,dict) and all(x in v for x in ('image','x','y','w','h')) for k,v in data.items() if not str(k).startswith('_'))
def opaque_edges(image,rect,threshold=64,share=0.9):
 x,y,w,h=rect;a=image.getchannel('A')
 sides=[[a.getpixel((x+i,y)) for i in range(w)],[a.getpixel((x+i,y+h-1)) for i in range(w)],[a.getpixel((x,y+j)) for j in range(h)],[a.getpixel((x+w-1,y+j)) for j in range(h)]]
 return all(sum(v>threshold for v in side)>=share*len(side) for side in sides)
def edge_fragments(comps,rect,main_area,others=None):
 x,y,w,h=rect;out=[]
 for n,c in comps:
  if n>=main_area:continue
  b=c['bbox'];bx0,by0,bx1,by1=max(b[0],x),max(b[1],y),min(b[2],x+w),min(b[3],y+h)
  touch=bx0<=x or by0<=y or bx1>=x+w or by1>=y+h
  thin=(bx1-bx0)<=max(3,0.2*w) or (by1-by0)<=max(3,0.2*h)
  if others is not None and touch and thin:
   # Packed (trimmed) atlas: the rect is the sprite's own bbox, so its outer sparkles and tips always touch an edge.
   # A neighbour's sliver either lies in that neighbour's rect or is a strip running along the edge (calibrated on 71 plists).
   sides=[(by1-by0,bx1-bx0,h) for hit in (by0<=y,by1>=y+h) if hit]+[(bx1-bx0,by1-by0,w) for hit in (bx0<=x,bx1>=x+w) if hit]
   strip=any(t<=max(3,0.2*d) and L>=4*t for t,L,d in sides)
   neighbour=any(bx0<ox+ow and ox<bx1 and by0<oy+oh and oy<by1 for ox,oy,ow,oh in others)
   thin=strip or neighbour
  if touch and thin:out.append([bx0,by0,bx1-bx0,by1-by0])
 return out
def grow(rect,e):return [rect[0]-e,rect[1]-e,rect[2]+2*e,rect[3]+2*e]
def extrusion(image,walls,threshold=64,tol=8,most=4):
 # TexturePacker "extrude N" repeats each sprite's edge pixels N px outward. Ring k (outside the rect) copies the edge
 # in >=90% of its opaque pixels on extruded sheets; on plain sheets opaque ring pixels are rare cuts or neighbours.
 px=image.load();W,H=image.size;e=0
 for k in range(1,most+1):
  n=same=0
  for x,y,w,h in walls[:400]:
   for i in range(0,w,max(1,w//24)):
    for p,q in (((x+i,y),(x+i,y-k)),((x+i,y+h-1),(x+i,y+h-1+k))):
     if 0<=q[1]<H and px[q][3]>threshold:n+=1;same+=max(abs(a-b) for a,b in zip(px[p],px[q]))<=tol
   for j in range(0,h,max(1,h//24)):
    for p,q in (((x,y+j),(x-k,y+j)),((x+w-1,y+j),(x+w-1+k,y+j))):
     if 0<=q[0]<W and px[q][3]>threshold:n+=1;same+=max(abs(a-b) for a,b in zip(px[p],px[q]))<=tol
  if n<50 or same<0.9*n:break
  e=k
 return e
def packed_components(image,rect,walls,extrude=0,pad=32,threshold=64):
 # Packers (TexturePacker, padding 0) let neighbouring sprites touch. Pixels inside another frame's rect (plus its
 # extrusion ring) belong to that frame, so they are hidden before tracing this frame's bodies; spill into unowned
 # texture still counts as a cut. This frame's own extrusion ring stays visible so a body running past it stays joined.
 x,y,w,h=rect;e=extrude;box=(max(0,x-pad),max(0,y-pad),min(image.width,x+w+pad),min(image.height,y+h+pad));win=image.crop(box);a=win.getchannel('A');orig=a.copy()
 local=lambda r:(max(0,r[0]-box[0]),max(0,r[1]-box[1]),max(0,r[0]+r[2]-box[0]),max(0,r[1]+r[3]-box[1]))
 others=[r for r in walls if r!=rect and r[0]-e<box[2] and box[0]<r[0]+r[2]+e and r[1]-e<box[3] and box[1]<r[1]+r[3]+e]
 for r in others:a.paste(0,local(grow(r,e)))
 own=local(grow(rect,e));a.paste(orig.crop(own),own[:2])
 for r in others:a.paste(0,local(r))
 own=local(rect);a.paste(orig.crop(own),own[:2]);win.putalpha(a);cs=components(win,threshold)
 for c in cs.values():
  b=c['bbox'];c['bbox']=[b[0]+box[0],b[1]+box[1],b[2]+box[0],b[3]+box[1]];c['runs']=[(x0+box[0],x1+box[0],yy+box[1]) for x0,x1,yy in c['runs']]
 return cs,[r for r in others if not (r[0]<=x and r[1]<=y and r[0]+r[2]>=x+w and r[1]+r[3]>=y+h)]

def audit(manifest_path,out=None,only=None):
 manifest_path=Path(manifest_path);cache={};issues=[];rows=[]
 from flat_atlas_adapter import is_flat_atlas,normalize
 if manifest_path.suffix.lower()=='.plist':
  # TexturePacker / Cocos sprite sheets: same roles and checks, the adapter only converts geometry.
  raw=plist.load(manifest_path)
  if not plist.is_plist_atlas(raw):raise ValueError('not_a_plist_atlas: '+str(manifest_path))
  manifest=plist.normalize(manifest_path,raw,only)
 else:
  manifest=json.loads(manifest_path.read_text())
  if is_flat_atlas(manifest) or _flat_any(manifest):
   raw_flat=manifest;manifest=normalize(manifest_path,manifest,only or sorted(k for k in manifest if not str(k).startswith('_')))
   # art patch v3 (2026-10-31): the adapter gives every listed frame single_body, which turned unprefixed multi-word picture text into
   # foreign_alpha_island (BalloonRun txt_Profile_Revisit). A frame without its own slice_role takes the default by
   # name below (icon_/node_/btn_/digit_N single_body, the rest scope_body), the same as frames.json.
   for k,f in manifest['frames'].items():
    if not (isinstance(raw_flat.get(k),dict) and raw_flat[k].get('slice_role')):f.pop('slice_role',None)
  elif only:
   if set(only)-set(manifest['frames']):raise ValueError('declared_frames_missing')
   manifest=dict(manifest,frames={k:v for k,v in manifest['frames'].items()if k in set(only)})
 if not manifest['frames']:raise ValueError('empty_declared_frames')
 skipped=[]
 if out:Path(out).mkdir(parents=True,exist_ok=True)
 for name,frame in manifest['frames'].items():
  # Only standalone UI silhouettes have this contract. Titles and punctuation can
  # have intentional detached pieces; those require an explicit different role.
  role=frame.get('slice_role')
  if role=='tileset':skipped.append({'frame':name,'reason':'slice_role tileset'});continue
  if role and role not in ('single_body','two_marks','multi_body'):
   issues.append({'frame':name,'kind':'unsupported_slice_role'});continue
  if role=='multi_body' and not frame.get('part_reason'):
   issues.append({'frame':name,'kind':'multipart_reason_missing'});continue
  base=frame.get('role_name',name)  # plist frame names carry ".png" and folders; roles read the bare file name
  if not role:
   if base.startswith(('icon_','node_','btn_')) or (base.startswith('digit_') and base[-1:].isdigit()):role='single_body'
   elif base=='digit_:':role='multi_body'
   elif (TILE_NAME.search(base) and not ('role_name' in frame and AUTO_TILE.fullmatch(base))) or frame.get('sliced') or frame.get('tiled'):skipped.append({'frame':name,'reason':'tileset/sliced name'});continue
   else:role='scope_body'
  if role not in ('single_body','two_marks','multi_body','scope_body'):continue
  tex=Path(frame['texture_file']) if frame.get('texture_file') else manifest_path.parent/(frame['texture']+'.png')
  if role=='scope_body' and not tex.is_file():skipped.append({'frame':name,'reason':'texture missing: '+tex.name});continue
  walls=manifest.get('packed_rects');others=None
  if str(tex) not in cache:
   image=Image.open(tex).convert('RGBA');cache[str(tex)]=(image,components(image) if walls is None else {},0 if walls is None else extrusion(image,walls))
  image,cs,ext=cache[str(tex)];rect=frame['rect']
  if not isinstance(rect,list) or len(rect)!=4 or not all(isinstance(x,int) for x in rect) or min(rect[:2])<0 or min(rect[2:])<=0 or rect[0]+rect[2]>image.width or rect[1]+rect[3]>image.height:
   issues.append({'frame':name,'kind':'invalid_or_out_of_texture_rect'});continue
  if role=='scope_body' and opaque_edges(image,rect):skipped.append({'frame':name,'reason':'opaque to all four edges (tile)'});continue
  if walls is not None:cs,others=packed_components(image,rect,walls,ext)
  visible=sorted([(inside(c,rect),c) for c in cs.values()],key=lambda q:-q[0]);visible=[q for q in visible if q[0]>0]
  if not visible:issues.append({'frame':name,'kind':'empty_slice'});continue
  area=visible[0][0];significant=[q for q in visible if q[0]>=max(24,area*.005)]
  row={'frame':name,'texture':str(tex),'texture_sha256':hashlib.sha256(tex.read_bytes()).hexdigest(),'rect':rect,'role':role,'components':[{'visible_area':n,'full_area':c['area'],'bbox':c['bbox']} for n,c in significant],'problems':[]}
  expected=2 if role=='two_marks' else 1
  if role not in ('multi_body','scope_body') and len(significant)>expected:row['problems'].append('foreign_alpha_island')
  if role not in ('multi_body','scope_body') and len(significant)<expected:row['problems'].append('declared_part_missing')
  if ext:row['extrude']=ext
  for n,c in significant:
   kept=inside(c,grow(rect,ext)) if ext else n  # the packer's extrusion copies are not lost body
   if c['area']-kept>=max(24,c['area']*.002):row['problems'].append('connected_body_cut_by_rect')
  if role=='scope_body':
   strips=edge_fragments(significant,rect,area,others)
   if strips:row['problems'].append('edge_fragment');row['edge_fragments']=strips
  row['problems']=sorted(set(row['problems']));rows.append(row)
  for problem in row['problems']:issues.append({'frame':name,'kind':problem,'rect':rect,'components':row['components']})
  if out:
   x,y,w,h=rect;crop=image.crop((x,y,x+w,y+h));crop=crop.rotate(90,expand=True) if frame.get('rotated') else crop;board=Image.new('RGBA',crop.size,'#e6dfd0');board.alpha_composite(crop);board.convert('RGB').save(Path(out)/(name.replace(':','colon').replace('/','slash')+'-slice.png'))
   if row['problems']:
    pad=45;box=[max(0,x-pad),max(0,y-pad),min(image.width,x+w+pad),min(image.height,y+h+pad)];neighbour=image.crop(box);bg=Image.new('RGBA',neighbour.size,'#e6dfd0');bg.alpha_composite(neighbour);draw=ImageDraw.Draw(bg);draw.rectangle((x-box[0],y-box[1],x+w-box[0]-1,y+h-box[1]-1),outline='#e43937',width=3);bg.convert('RGB').save(Path(out)/(name.replace(':','colon').replace('/','slash')+'-context.png'))
 return {'tool':'audit_atlas_slices','passed':not issues,'manifest':str(manifest_path.resolve()),'manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),'checked':len(rows),'issues':issues,'frames':rows,'declared_frames':{k:v['rect']for k,v in manifest['frames'].items()},'runtime_frames':{k:v.get('runtime_rect',v['rect'])for k,v in manifest['frames'].items()},'runtime_sizes':manifest.get('runtime_sizes',{}),'frame_names':{k:v.get('names',[k])for k,v in manifest['frames'].items()},'adapter':manifest.get('adapter','frames_v1'),'skipped':skipped,'scope':'v7.8: every slice. icon_/node_/btn_/digit_ = one body; other slices (picture text, pieces, projectiles, obstacles) = body not cut and no edge strip; tilesets/sliced plates/opaque tiles skipped (listed). .plist roles use the bare frame name; rotated frames are checked where they sit in the texture.'}


def check_project(project,dumps=None,out=None,only=None):
 project=Path(project)
 roots=[project/'assets'] if (project/'assets').is_dir() and not (project/'game.js').exists() else [project/'src'] if (project/'src').is_dir() and not (project/'game.js').exists() else [project]
 manifests=[]
 for root in roots:
  for path in sorted(set(root.rglob('frames.json'))|set(root.rglob('atlas.json'))|set(root.rglob('*.plist'))):
   if set(path.relative_to(root).parts)&{'test','tests','docs','node_modules','.git','build','simulation'}:continue
   if path.suffix=='.plist':
    # Only sprite sheets (frames + metadata); particle plists, Info.plist and the like are not atlases.
    if plist.is_plist_atlas(plist.load(path)):manifests.append(path)
    continue
   try:
    value=json.loads(path.read_text())
    from flat_atlas_adapter import is_flat_atlas
    if (isinstance(value.get('frames'),dict) and isinstance(value.get('textures'),dict)) or is_flat_atlas(value) or _flat_any(value):manifests.append(path)
   except (OSError,ValueError):continue
 results=[];expected={};sizes={};issues=[]
 for i,path in enumerate(sorted(manifests)):
  if path.suffix=='.plist':available={alt for name,frame in plist.load(path)['frames'].items() for alt in plist.names_of(name,frame)}
  else:raw=json.loads(path.read_text());available=set(raw.get('frames',raw))
  chosen=sorted(set(only)&available) if only else None
  if only and not chosen:continue
  results.append(audit(path,Path(out)/('atlas-'+str(i)) if out else None,chosen))
  r=results[-1]
  for name,rect in r['runtime_frames'].items():
   # A dump may name a plist frame with or without ".png", by its folder-less name or by a format-3 alias.
   for key in r['frame_names'].get(name,[name]):
    expected.setdefault(key,[]).append(rect);sizes.setdefault(key,[]).extend(r['runtime_sizes'].get(name,[rect[2:]] if rect else []))
  issues+=r['issues']
 if only and set(only)-set(expected):issues.append({'kind':'declared_frames_missing','frames':sorted(set(only)-set(expected))})
 observed=0
 if dumps:
  for path in Path(dumps).rglob('*.json'):
   try:j=json.loads(path.read_text())
   except (OSError,ValueError):continue
   if not isinstance(j,dict):continue
   runtime=j.get('frames')
   if isinstance(runtime,dict) and all(isinstance(v,list) and len(v)==4 for v in runtime.values()):
    for name,rect in runtime.items():
     if name in expected:
      observed+=1
      if rect not in expected[name]:issues.append({'frame':name,'kind':'runtime_rect_differs_from_manifest','runtime':rect,'expected':expected[name],'evidence':str(path)})
   for node in j.get('nodes',[]):
    sf=node.get('comps',{}).get('sprite',{});name=sf.get('frame');size=sf.get('frame_size')
    if name in expected and size:
     observed+=1
     if list(size) not in sizes[name]:issues.append({'frame':name,'kind':'runtime_size_differs_from_manifest','runtime_size':size,'expected':expected[name],'evidence':str(path)})
  if manifests and not observed:issues.append({'kind':'runtime_atlas_evidence_missing'})
 return {'tool':'audit_atlas_slices','applicable':bool(manifests),'passed':not issues,'checked':sum(x['checked'] for x in results),'runtime_observations':observed,'issues':issues,'atlases':results,'scope':'Transparent frames.json, flat atlas.json image/x/y/w/h and TexturePacker/Cocos .plist (format 0-3) atlases; v7.8 roles per audit().'}

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--manifest',type=Path);parser.add_argument('--project',type=Path);parser.add_argument('--dumps',type=Path);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--frames',help='comma-separated exact affected frame names; local scope only');a=parser.parse_args()
 if bool(a.manifest)==bool(a.project):parser.error('give exactly one of --manifest or --project')
 only=a.frames.split(',') if a.frames else None
 r=audit(a.manifest,a.out,only) if a.manifest else check_project(a.project,a.dumps,a.out,only)
 a.out.mkdir(parents=True,exist_ok=True);(a.out/'report.json').write_text(json.dumps(r,indent=2));print(json.dumps({'passed':r['passed'],'applicable':r.get('applicable',True),'checked':r['checked'],'runtime_observations':r.get('runtime_observations'),'issues':[{'frame':x.get('frame'),'kind':x['kind']} for x in r['issues']]}));raise SystemExit(not r['passed'])
