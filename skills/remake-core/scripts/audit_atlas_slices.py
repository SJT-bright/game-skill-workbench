from pathlib import Path
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

import argparse,json,hashlib
from PIL import ImageDraw

def audit(manifest_path,out=None,only=None):
 manifest_path=Path(manifest_path);manifest=json.loads(manifest_path.read_text());cache={};issues=[];rows=[]
 from flat_atlas_adapter import is_flat_atlas,normalize
 if is_flat_atlas(manifest):manifest=normalize(manifest_path,manifest,only)
 elif only:
  if set(only)-set(manifest['frames']):raise ValueError('declared_frames_missing')
  manifest=dict(manifest,frames={k:v for k,v in manifest['frames'].items()if k in set(only)})
 if not manifest['frames']:raise ValueError('empty_declared_frames')
 if out:Path(out).mkdir(parents=True,exist_ok=True)
 for name,frame in manifest['frames'].items():
  # Only standalone UI silhouettes have this contract. Titles and punctuation can
  # have intentional detached pieces; those require an explicit different role.
  role=frame.get('slice_role')
  if role and role not in ('single_body','two_marks','multi_body'):
   issues.append({'frame':name,'kind':'unsupported_slice_role'});continue
  if role=='multi_body' and not frame.get('part_reason'):
   issues.append({'frame':name,'kind':'multipart_reason_missing'});continue
  if not role:
   if name.startswith(('icon_','node_','btn_')) or (name.startswith('digit_') and name[-1:].isdigit()):role='single_body'
   elif name=='digit_:':role='multi_body'
   else:continue
  if role not in ('single_body','two_marks','multi_body'):continue
  tex=manifest_path.parent/(frame['texture']+'.png')
  if str(tex) not in cache:
   image=Image.open(tex).convert('RGBA');cache[str(tex)]=(image,components(image))
  image,cs=cache[str(tex)];rect=frame['rect']
  if not isinstance(rect,list) or len(rect)!=4 or not all(isinstance(x,int) for x in rect) or min(rect[:2])<0 or min(rect[2:])<=0 or rect[0]+rect[2]>image.width or rect[1]+rect[3]>image.height:
   issues.append({'frame':name,'kind':'invalid_or_out_of_texture_rect'});continue
  visible=sorted([(inside(c,rect),c) for c in cs.values()],key=lambda q:-q[0]);visible=[q for q in visible if q[0]>0]
  if not visible:issues.append({'frame':name,'kind':'empty_slice'});continue
  area=visible[0][0];significant=[q for q in visible if q[0]>=max(24,area*.005)]
  row={'frame':name,'texture':str(tex),'texture_sha256':hashlib.sha256(tex.read_bytes()).hexdigest(),'rect':rect,'role':role,'components':[{'visible_area':n,'full_area':c['area'],'bbox':c['bbox']} for n,c in significant],'problems':[]}
  expected=2 if role=='two_marks' else 1
  if role!='multi_body' and len(significant)>expected:row['problems'].append('foreign_alpha_island')
  if role!='multi_body' and len(significant)<expected:row['problems'].append('declared_part_missing')
  for n,c in significant:
   if c['area']-n>=max(24,c['area']*.002):row['problems'].append('connected_body_cut_by_rect')
  row['problems']=sorted(set(row['problems']));rows.append(row)
  for problem in row['problems']:issues.append({'frame':name,'kind':problem,'rect':rect,'components':row['components']})
  if out:
   x,y,w,h=rect;crop=image.crop((x,y,x+w,y+h));board=Image.new('RGBA',crop.size,'#e6dfd0');board.alpha_composite(crop);board.convert('RGB').save(Path(out)/(name.replace(':','colon').replace('/','slash')+'-slice.png'))
   if row['problems']:
    pad=45;box=[max(0,x-pad),max(0,y-pad),min(image.width,x+w+pad),min(image.height,y+h+pad)];neighbour=image.crop(box);bg=Image.new('RGBA',neighbour.size,'#e6dfd0');bg.alpha_composite(neighbour);draw=ImageDraw.Draw(bg);draw.rectangle((x-box[0],y-box[1],x+w-box[0]-1,y+h-box[1]-1),outline='#e43937',width=3);bg.convert('RGB').save(Path(out)/(name.replace(':','colon').replace('/','slash')+'-context.png'))
 return {'tool':'audit_atlas_slices','passed':not issues,'manifest':str(manifest_path.resolve()),'manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),'checked':len(rows),'issues':issues,'frames':rows,'declared_frames':{k:v['rect']for k,v in manifest['frames'].items()},'adapter':manifest.get('adapter','frames_v1'),'scope':'Declared standalone UI silhouettes and single glyphs; intended multipart art needs an explicit role and normal control.'}


def check_project(project,dumps=None,out=None,only=None):
 project=Path(project)
 roots=[project/'assets'] if (project/'assets').is_dir() and not (project/'game.js').exists() else [project/'src'] if (project/'src').is_dir() and not (project/'game.js').exists() else [project]
 manifests=[]
 for root in roots:
  for path in sorted(set(root.rglob('frames.json'))|set(root.rglob('atlas.json'))):
   if set(path.relative_to(root).parts)&{'test','tests','docs','node_modules','.git','build','simulation'}:continue
   try:
    value=json.loads(path.read_text())
    from flat_atlas_adapter import is_flat_atlas
    if (isinstance(value.get('frames'),dict) and isinstance(value.get('textures'),dict)) or is_flat_atlas(value):manifests.append(path)
   except (OSError,ValueError):continue
 results=[];expected={};issues=[]
 for i,path in enumerate(sorted(manifests)):
  raw=json.loads(path.read_text());available=set(raw.get('frames',raw));chosen=sorted(set(only)&available) if only else None
  if only and not chosen:continue
  results.append(audit(path,Path(out)/('atlas-'+str(i)) if out else None,chosen))
  for name,rect in results[-1]['declared_frames'].items():expected.setdefault(name,[]).append(rect)
  issues+=results[-1]['issues']
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
     if list(size) not in [x[2:] for x in expected[name]]:issues.append({'frame':name,'kind':'runtime_size_differs_from_manifest','runtime_size':size,'expected':expected[name],'evidence':str(path)})
  if manifests and not observed:issues.append({'kind':'runtime_atlas_evidence_missing'})
 return {'tool':'audit_atlas_slices','applicable':bool(manifests),'passed':not issues,'checked':sum(x['checked'] for x in results),'runtime_observations':observed,'issues':issues,'atlases':results,'scope':'Transparent frames.json and flat atlas.json image/x/y/w/h protocols; declared single-body scope only.'}

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--manifest',type=Path);parser.add_argument('--project',type=Path);parser.add_argument('--dumps',type=Path);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--frames',help='comma-separated exact affected frame names; local scope only');a=parser.parse_args()
 if bool(a.manifest)==bool(a.project):parser.error('give exactly one of --manifest or --project')
 only=a.frames.split(',') if a.frames else None
 r=audit(a.manifest,a.out,only) if a.manifest else check_project(a.project,a.dumps,a.out,only)
 a.out.mkdir(parents=True,exist_ok=True);(a.out/'report.json').write_text(json.dumps(r,indent=2));print(json.dumps({'passed':r['passed'],'applicable':r.get('applicable',True),'checked':r['checked'],'runtime_observations':r.get('runtime_observations'),'issues':[{'frame':x.get('frame'),'kind':x['kind']} for x in r['issues']]}));raise SystemExit(not r['passed'])
