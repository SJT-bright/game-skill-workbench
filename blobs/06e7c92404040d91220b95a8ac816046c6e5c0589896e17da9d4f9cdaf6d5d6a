"""Normalize the explicit image/x/y/w/h atlas protocol; never guess missing textures."""
from pathlib import Path
import json

def is_flat_atlas(data):
 return isinstance(data,dict) and any(str(k).startswith(('btn_','icon_','node_')) and isinstance(v,dict) and all(x in v for x in ('image','x','y','w','h')) for k,v in data.items())

def normalize(path,data,only=None):
 path=Path(path).resolve();root=next((p for p in path.parents if (p/'assets').is_dir()),None)
 if root is None:raise ValueError('flat_atlas_project_root_missing: '+str(path))
 selected=set(only) if only else {k for k in data if k.startswith(('btn_','icon_','node_'))}
 if not selected or selected-set(data):raise ValueError('flat_atlas_declared_frames_missing')
 frames={};textures={}
 for name in sorted(selected):
  frame=data[name]
  if not isinstance(frame,dict)or not all(k in frame for k in ('image','x','y','w','h')):raise ValueError('flat_atlas_frame_schema: '+name)
  suffix=str(frame['image']).removesuffix('.png')+'.png'
  candidates=[p for p in (root/'assets').rglob(Path(suffix).name)if p.as_posix().endswith('/'+suffix)]
  if len(candidates)!=1:raise ValueError('flat_atlas_texture_not_unique: '+name+' '+str(candidates))
  texture=str(candidates[0].resolve().with_suffix(''));textures[texture]={}
  frames[name]={'texture':texture,'rect':[frame[k]for k in ('x','y','w','h')],'slice_role':frame.get('slice_role','single_body')}
  if frame.get('part_reason'):frames[name]['part_reason']=frame['part_reason']
 return {'textures':textures,'frames':frames,'adapter':'flat_image_xywh_v1','scope':sorted(selected)}
