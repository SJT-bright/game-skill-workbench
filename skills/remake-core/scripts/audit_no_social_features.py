#!/usr/bin/env python3
"""Reject game-owned sharing and social/global ranking before design and on current exports; static evidence only.

Saul 2026-10-31: places inside one match against local bots, the result place, local trophies by place, trophies ->
tier, personal stars and best score are allowed (68 小熊拳击). So rank / setRank / getRank / RANKED / RankView names are
NOT blocked by name any more. Still blocked: platform ranking / open-data APIs, board wording or node names scoped to
the world / friends / a region / a week / a server ("World Rank", "friendsLeaderboard", 好友排行, 周榜 ...), inflated
made-up places ("You are #3,512", "Top 5%"), fake leagues (league / LeagueSim) and every share / invite entry.
"""
import argparse,hashlib,json,re
from pathlib import Path
SHARE_API=r'shareToStory|onCopyUrl|shareAppMessage|onShareAppMessage|showShareMenu|updateShareMenu|onShareTimeline|shareMessageToFriend|shareToFriend|shareVideoMessage|createGameRecorderShareButton'
RANK_API=r'getFriendCloudStorage|getGroupCloudStorage|getUserCloudStorage|setUserCloudStorage|removeUserCloudStorage|setImRankData|getImRankList|showImRankList|subscribeSystemMessageRank|getOpenDataContext'
CALL=re.compile(r'\b(?:'+SHARE_API+'|'+RANK_API+r')\s*\(|\bnavigator\s*\.\s*share\s*\(')
# Names and visible words that are always out: share / invite entries, the friend board, fake leagues, Chinese board words.
ENTITY=re.compile(r'(?:^|[^a-z])(?:friendrank|league|share(?:btn|button|panel|view)?|invite(?:btn|button)?)(?:$|[^a-z])|排行榜|好友排行|好友榜|全服排|全球排|世界排|地区排|全国排|周榜|月榜|总榜|分享给好友|邀请好友|炫耀成绩',re.I)
MODULE=re.compile(r'\b(?:LeagueSim|ShareView|InviteView)\b')
# Open-data (friend board) view components in prefabs / scenes, and game code drawing the open-data canvas.
OPEN_DATA_TYPE=re.compile(r'^cc\.(?:WX|TT)?SubContextView$')
# Only the game-side "draw the open-data canvas into a texture" call; the platform adapter.js itself reads
# window.sharedCanvas (云朵小兔 build/bytedance/adapter.js), so the bare name is not evidence.
OPEN_DATA_JS=re.compile(r'initWithElement\s*\(\s*(?:window\s*\.\s*)?sharedCanvas\b')
# A board word next to a social / global scope word (either order, at most one token between).
SCOPE={'global','world','worldwide','friend','friends','regional','region','country','national','weekly','monthly','server','online'}
BOARD={'rank','ranks','ranking','rankings','ranked','ranklist','leaderboard','leaderboards','standing','standings'}
# Made-up global places: "#3,512", "#3512" in label text, "Top 5%", "better than 87% of players".
BIG_PLACE=re.compile(r'#\s?\d{1,3}(?:,\d{3})+(?!\d)')
BIG_PLACE_LABEL=re.compile(r'(?<![0-9A-Za-z])#\s?\d{4,}(?![0-9A-Za-z])')
PERCENTILE=re.compile(r'\btop\s*\d+(?:\.\d+)?\s*%|\b(?:better than|beat|beats|ahead of|surpass(?:ed|es)?)\s*\d+(?:\.\d+)?\s*%\s*of\s*(?:all\s*)?(?:players|people|users)',re.I)
LITERAL=re.compile(r'''(["'`])((?:\\.|(?!\1)[^\\\n])*)\1''')
SKIP={'node_modules','library','temp','.git','__pycache__'}
def tokens(s):
 t=[x.lower()for x in re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+',s)];out=[]
 for x in t:
  if x=='board'and out and out[-1]=='leader':out[-1]='leaderboard'
  else:out.append(x)
 return out
def scoped_board(s):
 t=tokens(s)
 for i,x in enumerate(t):
  if x in BOARD and any(y in SCOPE for y in t[max(0,i-2):i+3]):return True
 return False
def social_words(s):
 """Visible wording / node name that names a social or global board."""
 return bool(ENTITY.search(s)or scoped_board(s))
def fake_place(s,label):
 return bool(BIG_PLACE.search(s)or PERCENTILE.search(s)or(label and BIG_PLACE_LABEL.search(s)))
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
   
   if p.name.lower() in {'share.png.meta','invite.png.meta','邀请好友.png.meta'} or any(v in {'friendrank','league'}for v in low[:-1]):add(p,'feature_asset',str(rel))
   text=p.read_text(errors='replace');files[label+'/'+str(rel)]=hashlib.sha256(p.read_bytes()).hexdigest()
   if p.suffix in{'.ts','.js'}:
    if p.name.endswith('.d.ts'):continue
    for m in CALL.finditer(text):add(p,'business_api',m.group())
    for m in MODULE.finditer(text):add(p,'feature_module',m.group())
    if 'subcontext'not in low:
     for m in OPEN_DATA_JS.finditer(text):add(p,'open_data_canvas',m.group())
    # String literals: only the scoped-board wording and made-up places (share / league names keep their old scope).
    for m in LITERAL.finditer(text):
     v=m.group(2)
     # display text only (has a space, not a route / URL): vendor SDK routes like 'Home/Rank/getFriendRank' bundled into
     # index.js are not player-facing wording (FoxDenDash build); business calls are caught by CALL instead.
     if ' 'in v.strip()and'/'not in v and scoped_board(v):add(p,'social_board_text',v)
     elif fake_place(v,False):add(p,'fake_global_place',v)
   if p.suffix in{'.prefab','.fire','.scene','.json'}:
    try:data=json.loads(text)
    except ValueError:continue
    def walk(x):
     if isinstance(x,dict):
      for k,v in x.items():
       if not isinstance(v,str):continue
       if k=='__type__'and OPEN_DATA_TYPE.match(v):add(p,'open_data_view',v)
       if k in{'_name','name','text','string','_string','path','open','button','screen','purpose'}:
        if social_words(v):add(p,'ui_or_route',v)
        elif fake_place(v,k in{'text','string','_string'}):add(p,'fake_global_place',v)
      for v in x.values():walk(v)
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
 return{'tool':'audit_no_social_features','policy':'no_social_features.2026-10-31','passed':not hits,'findings':hits,'artifacts':files,'excluded_third_party':excluded,'scope':'Static source/export/UI evidence; local in-match places vs bots are allowed (Saul 2026-10-31); actual mobile navigation and platform-menu checks remain required'}
def main():
 a=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);a.add_argument('--project',type=Path,required=True)
 for n in ['web','native','dumps','out']:a.add_argument('--'+n,type=Path)
 a.add_argument('--stage',choices=['pre_design','implementation','final'],default='pre_design');x=a.parse_args();r=audit(x.project,x.web,x.native,x.dumps);r['stage']=x.stage
 if x.out:x.out.parent.mkdir(parents=True,exist_ok=True);x.out.write_text(json.dumps(r,ensure_ascii=False,indent=2))
 print(json.dumps({'passed':r['passed'],'findings':r['findings'],'inspected':len(r['artifacts'])},ensure_ascii=False));return 0 if r['passed']else 2
if __name__=='__main__':raise SystemExit(main())
