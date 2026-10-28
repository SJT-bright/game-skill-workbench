#!/usr/bin/env python3
"""Reject game-owned sharing/ranking before design and on current exports; static evidence only."""
import argparse,hashlib,json,re
from pathlib import Path
CALL=re.compile(r'\b(?:shareToStory|onCopyUrl|shareAppMessage|onShareAppMessage|showShareMenu|updateShareMenu|onShareTimeline|shareMessageToFriend|shareToFriend|shareVideoMessage|createGameRecorderShareButton|getRank|setRank|getFriendCloudStorage|getGroupCloudStorage|setUserCloudStorage|setImRankData|getImRankList|showImRankList|subscribeSystemMessageRank)\s*\(|\bnavigator\s*\.\s*share\s*\(')
ENTITY=re.compile(r'(?:^|[^a-z])(?:rank(?:ing|ings|view|item|panel|btn|button)?|leaderboard|friendrank|league|share(?:btn|button|panel|view)?|invite(?:btn|button)?)(?:$|[^a-z])|排行榜|好友排行|分享给好友|邀请好友|炫耀成绩',re.I)
MODULE=re.compile(r'\b(?:RankView|RankItem|RankingView|LeaderboardView|LeagueSim|ShareView|InviteView)\b')
SKIP={'node_modules','library','temp','.git','__pycache__'}
def audit(project,web=None,native=None,dumps=None):
 project=Path(project);roots={'source':project/'assets'}
 for k,p in [('web',web),('native',native),('dumps',dumps)]:
  if p:roots[k]=Path(p)
 hits=[];files={};excluded=[]
 def add(p,kind,value):hits.append({'file':str(p),'kind':kind,'match':str(value)[:180]})
 for label,root in roots.items():
  if not root.is_dir():add(root,'missing_root',label);continue
  for p in sorted(root.rglob('*')):
   if not p.is_file()or SKIP.intersection(p.relative_to(root).parts)or p.suffix not in{'.ts','.js','.json','.prefab','.fire','.scene','.meta'}:continue
   rel=p.relative_to(root);low=[v.lower()for v in rel.parts]
   if label!='dumps'and any(v in{'sdk','vendor','cocos','subcontext'}for v in low):
    # Open-data subcontexts are player-facing ranking candidates, not vendor exceptions.
    if 'subcontext'not in low:excluded.append(str(p));continue
   if p.name in{'adapter-min.js','weapp-adapter.js','cocos2d-js-min.js'}:excluded.append(str(p));continue
   
   if p.name.lower() in {'share.png.meta','invite.png.meta','邀请好友.png.meta'} or any(v in {'rank','leaderboard'}for v in low):add(p,'feature_asset',str(rel))
   text=p.read_text(errors='replace');files[label+'/'+str(rel)]=hashlib.sha256(p.read_bytes()).hexdigest()
   if p.suffix in{'.ts','.js'}:
    if p.name.endswith('.d.ts'):continue
    for m in CALL.finditer(text):add(p,'business_api',m.group())
    for m in MODULE.finditer(text):add(p,'feature_module',m.group())
   if p.suffix in{'.prefab','.fire','.scene','.json'}:
    try:data=json.loads(text)
    except ValueError:continue
    # Cocos 2.4 compiled SpriteFrames carry a resource name, not a UI route.
    # Exclude only the descriptor's name field; still inspect every other field,
    # and never exempt cc.Node/scene/prefab records or runtime API calls.
    sprite_descriptors=set()
    if isinstance(data,list) and len(data)==11 and data[0]==1 and data[3]==['cc.SpriteFrame'] and isinstance(data[5],list):
     for descriptor in data[5]:
      if isinstance(descriptor,dict) and all(key in descriptor for key in ('rect','offset','originalSize','capInsets')) and all(isinstance(descriptor[key],list) for key in ('rect','offset','originalSize','capInsets')):
       sprite_descriptors.add(id(descriptor))
    def walk(x):
     if isinstance(x,dict):
      for k,v in x.items():
       resource_name=k=='name' and id(x) in sprite_descriptors
       if not resource_name and k in{'_name','name','text','string','_string','path','open','button','screen','purpose'}and isinstance(v,str)and ENTITY.search(v):add(p,'ui_or_route',v)
       walk(v)
     elif isinstance(x,list):
      for v in x:walk(v)
    walk(data)
   if MODULE.search(p.stem):add(p,'feature_file',p.name)
 decision=project/'docs/league/decision.json'
 if decision.is_file():
  try:
   record=json.loads(decision.read_text())
   if not isinstance(record,dict) or record.get('decision') not in ('none','skip'):add(decision,'obsolete_enabling_decision',record)
   files['decision/league']=hashlib.sha256(decision.read_bytes()).hexdigest()
  except (ValueError,OSError):add(decision,'invalid_decision','unreadable ranking decision')
 return{'tool':'audit_no_social_features','policy':'no_social_features.2026-10-24','passed':not hits,'findings':hits,'artifacts':files,'excluded_third_party':excluded,'scope':'Static source/export/UI evidence; actual mobile navigation and platform-menu checks remain required'}
def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--project',type=Path,required=True)
 for n in ['web','native','dumps','out']:a.add_argument('--'+n,type=Path)
 a.add_argument('--stage',choices=['pre_design','implementation','final'],default='pre_design');x=a.parse_args();r=audit(x.project,x.web,x.native,x.dumps);r['stage']=x.stage
 if x.out:x.out.parent.mkdir(parents=True,exist_ok=True);x.out.write_text(json.dumps(r,ensure_ascii=False,indent=2))
 print(json.dumps({'passed':r['passed'],'findings':r['findings'],'inspected':len(r['artifacts'])},ensure_ascii=False));return 0 if r['passed']else 2
if __name__=='__main__':raise SystemExit(main())
