"""Source-PNG triage for named Cocos2 source/export standalone game sprites.
Signals need human comparison; not an art verdict or a full bundle-format verifier.
"""
import argparse,base64,hashlib,json,re
from collections import deque
from pathlib import Path

def decode(value):
    if not isinstance(value,str):raise ValueError('texture UUID must be a string')
    if len(value)==22:
        raw=value[:2]+base64.b64decode(value[2:],validate=True).hex()
        value='-'.join([raw[:8],raw[8:12],raw[12:16],raw[16:20],raw[20:]])
    if not re.fullmatch(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}',value):raise ValueError('unsupported texture UUID')
    return value

def runlen(values):
    best=length=0
    for item in values:length=length+1 if item else 0;best=max(best,length)
    return best

def inspect_texture(path):
    from PIL import Image
    with Image.open(path) as source:im=source.convert('RGBA')
    width,height=im.size;mask=bytearray(v>8 for v in im.getchannel('A').tobytes())
    if not any(mask):return {'size':[width,height],'suspects':['empty_alpha'],'edge_runs':{},'components':[]}
    edges={'top':mask[:width],'bottom':mask[-width:],'left':mask[::width],'right':mask[width-1::width]}
    cuts={key:runlen(values) for key,values in edges.items() if runlen(values)>=max(16,len(values)*.15)}
    remaining=mask[:];parts=[]
    for i in range(width*height):
        if not remaining[i]:continue
        queue=deque([i]);remaining[i]=0;area=0;box=[width,height,0,0]
        while queue:
            z=queue.popleft();area+=1;x=z%width;y=z//width
            box=[min(box[0],x),min(box[1],y),max(box[2],x+1),max(box[3],y+1)]
            for xx in range(max(0,x-1),min(width,x+2)):
                for yy in range(max(0,y-1),min(height,y+2)):
                    index=yy*width+xx
                    if remaining[index]:remaining[index]=0;queue.append(index)
        parts.append({'area':area,'bbox':box})
    parts.sort(key=lambda x:-x['area']);floor=max(12,parts[0]['area']*.0005)
    fragments=[c for c in parts[1:] if c['area']>=floor]
    margin=max(2,min(width,height)*.005);b=parts[0]['bbox'];touches=min(b[0],b[1],width-b[2],height-b[3])<margin
    signals=(['straight_source_edge'] if cuts else [])+(['extra_alpha_components'] if fragments else [])+(['main_body_lacks_safety_margin'] if touches else [])
    return {'size':[width,height],'suspects':signals,'edge_runs':cuts,'components':fragments,'main_component':parts[0],'alpha_threshold':8,'component_floor':floor,'pixel_sha256':hashlib.sha256(im.tobytes()).hexdigest()}

def check(root,names,role='single_body'):
    root=Path(root).resolve();names=list(dict.fromkeys(names));errors=[];matches={name:[] for name in names}
    if not root.is_dir() or not names or any(not isinstance(n,str) or not n for n in names):
        return {'input':str(root),'status':'incomplete','passed':False,'checked':0,'missing':names,'errors':['Cocos source/export root and nonempty frame targets required'],'rows':[],'art_verdict':'not_assessed'}
    if role not in ('single_body','background','tile','multi_body'):raise ValueError('unsupported role')
    if role!='single_body':
        return {'input':str(root),'status':'not_applicable','passed':None,'checked':0,'missing':[],'errors':[],'rows':[],'role':role,'art_verdict':'not_assessed'}
    source_mode=(root/'project.json').is_file()
    if source_mode:
        for p in (root/'assets').rglob('*.png.meta'):
            try:
                doc=json.loads(p.read_text())
                for name in set(doc.get('subMetas',{}))&set(names):
                    tex=Path(str(p)[:-5]).resolve()
                    if not tex.is_relative_to(root) or not tex.is_file():raise ValueError('missing source PNG')
                    matches[name].append(tex)
            except (OSError,ValueError,TypeError) as exc:errors.append({'path':str(p.relative_to(root)),'error':str(exc)})
    # Limited profile: standalone import/*.json + sibling native directory.
    # Scan both main assets and ordinary subpackages; unknown layouts remain incomplete.
    folders=[] if source_mode else sorted(set(root.glob('assets/*/import'))|set(root.glob('subpackages/*/import')))
    for folder in folders:
        for p in folder.rglob('*.json'):
            try:
                doc=json.loads(p.read_text())
                if not isinstance(doc,list) or len(doc)<6 or not isinstance(doc[5],list) or not doc[5] or not isinstance(doc[5][0],dict):continue
                name=doc[5][0].get('name')
                if name not in matches:continue
                uuid=decode(doc[1][0]);native=folder.parent/'native'
                textures=list(native.rglob(uuid+'.png'))
                if len(textures)!=1:raise ValueError('missing/ambiguous standalone PNG')
                path=textures[0].resolve()
                if not path.is_relative_to(root):raise ValueError('texture outside Native root')
                matches[name].append(path)
            except (OSError,ValueError,TypeError,IndexError,KeyError) as exc:
                errors.append({'path':str(p.relative_to(root)),'error':str(exc)})
    rows=[];cache={}
    for name,paths in matches.items():
        if len(paths)!=1:
            if len(paths)>1:errors.append({'frame':name,'error':'ambiguous frame name across bundles'})
            continue
        path=paths[0]
        try:
            if path not in cache:cache[path]=dict(inspect_texture(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            row=dict(cache[path],name=name,texture=str(path.relative_to(root)));rows.append(row)
        except (OSError,ValueError,ImportError) as exc:errors.append({'frame':name,'error':str(exc)})
    missing=sorted(set(names)-{row['name'] for row in rows});review=any(row['suspects'] for row in rows)
    status='incomplete' if missing or errors or not rows else 'needs_review' if review else 'no_signals'
    return {'input':str(root),'status':status,'passed':status=='no_signals','checked':len(rows),'missing':missing,'errors':errors,'rows':rows,'art_verdict':'not_assessed','coverage':'named standalone Cocos2 SpriteFrame/PNG source signals only; actual frame rect and whole-page composition need project observation'}

def captured_inventory(dumps):
    names=set();pages=set()
    if dumps:
        for path in Path(dumps).rglob('*.json'):
            try:doc=json.loads(path.read_text())
            except (OSError,ValueError):continue
            if not isinstance(doc,dict):continue
            nodes=doc.get('nodes',[])
            if not isinstance(nodes,list):continue
            for node in nodes:
                if not isinstance(node,dict):continue
                sprite=node.get('comps',{}).get('sprite',{});frame=sprite.get('frame')
                if isinstance(frame,str) and frame:names.add(frame)
            if nodes:pages.add(str(doc.get('page',path.name)))
    excluded=[{'frame':n,'reason':'background texture: separate composition/tiling review'} for n in sorted(names) if n.startswith('background_')]
    return {'pages':sorted(pages),'observed_frames':sorted(names),'selected_frames':sorted(n for n in names if not n.startswith('background_')),'excluded_frames':excluded}

def captured_frames(dumps):
    return captured_inventory(dumps)['selected_frames']

def apply_review(result):
    path=Path(result['input'])/'docs/art/sprite-source-review.json'
    if not path.is_file() or result['status']=='incomplete':return result
    try:entries=json.loads(path.read_text()).get('reviews',[])
    except (OSError,ValueError,TypeError):result['errors'].append('invalid sprite-source-review.json');result['status']='incomplete';result['passed']=False;return result
    if not isinstance(entries,list) or any(not isinstance(x,dict) or not isinstance(x.get('why',''),str) or not isinstance(x.get('normal_signals',[]),list) for x in entries):
        result['errors'].append('invalid source review entries');result['status']='incomplete';result['passed']=False;return result
    for row in result['rows']:
        for entry in entries:
            if entry.get('frame')!=row['name'] or entry.get('sha256')!=row['sha256'] or not entry.get('why','').strip():continue
            accepted=set(entry.get('normal_signals',[]))&{'straight_source_edge','main_body_lacks_safety_margin','extra_alpha_components'}
            row['observed_suspects']=row['suspects'][:];row['suspects']=[x for x in row['suspects'] if x not in accepted];row['human_review']=entry
    result['status']='needs_review' if any(r['suspects'] for r in result['rows']) else 'no_signals';result['passed']=result['status']=='no_signals'
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('native_root',type=Path,metavar='ROOT');parser.add_argument('frames',nargs='*');parser.add_argument('--dumps',type=Path);parser.add_argument('--out',type=Path);parser.add_argument('--role',choices=['single_body','background','tile','multi_body'],default='single_body');args=parser.parse_args()
    names=args.frames or captured_frames(args.dumps)
    result=apply_review(check(args.native_root,names,args.role))
    if args.dumps:result['capture_inventory']=captured_inventory(args.dumps)
    if args.out:args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 2 if result['status']=='incomplete' else 1 if result['status']=='needs_review' else 0
if __name__=='__main__':raise SystemExit(main())
