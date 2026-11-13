"""Normalize TexturePacker / Cocos .plist atlases (format 0-3) into the frames.json shape audit() reads; never guess missing textures."""
from pathlib import Path
import plistlib,re

EXT=re.compile(r'\.(png|jpe?g|webp|bmp|tga)$',re.I)
def base_name(name):
 # Role words live in the file name: "ui/btn_play.png" -> "btn_play". Cocos SpriteFrame.name drops the extension too.
 return EXT.sub('',str(name).replace('\\','/').rsplit('/',1)[-1])
def nums(value):
 return [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?',str(value))]
def ints(value,n):
 v=nums(value)
 if len(v)!=n:raise ValueError('plist_bad_geometry: '+str(value))
 return [int(round(x)) for x in v]

def load(path):
 try:return plistlib.loads(Path(path).read_bytes())
 except Exception:return None
def is_plist_atlas(data):
 # Sprite-sheet plists have a frames dict of frame dicts plus metadata; particle plists, Info.plist and others do not.
 return isinstance(data,dict) and isinstance(data.get('frames'),dict) and isinstance(data.get('metadata'),dict) and bool(data['frames']) and all(isinstance(v,dict) for v in data['frames'].values())
def names_of(name,frame=None):
 out=[name,base_name(name),EXT.sub('',str(name))]
 for alias in (frame or {}).get('aliases') or []:out+=[alias,base_name(alias)]
 return list(dict.fromkeys(out))

def frame_geometry(frame,fmt):
 """Return (texture rect [x,y,w,h] as stored in the texture, unrotated size [w,h], source size [w,h], rotated)."""
 if fmt==0 or 'x' in frame and 'width' in frame:
  x,y,w,h=(int(round(float(frame[k]))) for k in ('x','y','width','height'));rotated=False
  source=[int(round(float(frame.get('originalWidth',w)))),int(round(float(frame.get('originalHeight',h))))]
 elif 'textureRect' in frame:
  x,y,w,h=ints(frame['textureRect'],4);rotated=bool(frame.get('textureRotated'))
  source=ints(frame['spriteSourceSize'],2) if 'spriteSourceSize' in frame else [w,h]
 elif 'frame' in frame:
  x,y,w,h=ints(frame['frame'],4);rotated=bool(frame.get('rotated'))
  source=ints(frame['sourceSize'],2) if 'sourceSize' in frame else [w,h]
 else:raise ValueError('plist_frame_schema')
 # A rotated frame is stored 90 degrees turned: it covers h x w pixels in the texture.
 return ([x,y,h,w] if rotated else [x,y,w,h]),[w,h],[abs(source[0]),abs(source[1])],rotated

def texture_file(path,data):
 meta=data.get('metadata') or {};name=meta.get('realTextureFileName') or meta.get('textureFileName')
 if not name and isinstance(meta.get('target'),dict):name=meta['target'].get('textureFileName')
 return (Path(path).parent/str(name)) if name else None

def normalize(path,data,only=None):
 path=Path(path);fmt=int((data.get('metadata') or {}).get('format',2) or 0);tex=texture_file(path,data)
 if tex is None:tex=path.parent/(path.stem+'.metadata-has-no-textureFileName.png')
 lookup={}
 for name,frame in data['frames'].items():
  for alt in names_of(name,frame):lookup.setdefault(alt,name)
 if only:
  missing=[x for x in only if x not in lookup]
  if missing:raise ValueError('declared_frames_missing')
  selected=sorted({lookup[x] for x in only})
 else:selected=sorted(data['frames'])
 frames={};sizes={};walls=[]
 for name,raw in data['frames'].items():
  # Every frame's texture area, also under --frames: neighbours own their pixels (see audit packed_components).
  try:walls.append(frame_geometry(raw,fmt)[0])
  except (ValueError,KeyError,TypeError):pass
 for name in selected:
  raw=data['frames'][name]
  try:rect,size,source,rotated=frame_geometry(raw,fmt)
  except (ValueError,KeyError,TypeError):frames[name]={'texture':str(tex.with_suffix('')),'texture_file':str(tex),'rect':None,'role_name':base_name(name)};continue
  frames[name]={'texture':str(tex.with_suffix('')),'texture_file':str(tex),'rect':rect,'runtime_rect':rect[:2]+size,'rotated':rotated,'role_name':base_name(name),'names':names_of(name,raw)}
  # Explicit source roles have the same contract as frames.json. A transparent
  # outlined button can intentionally contain disconnected letters/icons; losing
  # its declared role incorrectly turns those own parts into foreign islands.
  for key in ('slice_role','part_reason'):
   if key in raw:frames[name][key]=raw[key]
  # ui_dump.js reports rect size for trimmed sprites and originalSize for trim=false sprites.
  sizes[name]=[size]+([source] if source and source!=size else [])
 return {'textures':{str(tex.with_suffix('')):{}},'frames':frames,'runtime_sizes':sizes,'packed_rects':walls,'adapter':'plist_format%d_v1'%fmt,'texture_file':str(tex),'scope':selected}
